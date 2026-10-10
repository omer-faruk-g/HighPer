#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — Gradle / Fabric performance analysis (READ-ONLY). Section D (D1–D6).

Reads <project>/gradle.properties and ~/.gradle/gradle.properties and reports:
  org.gradle.daemon, org.gradle.parallel, org.gradle.caching, org.gradle.jvmargs,
  org.gradle.configuration-cache  (D1). When both files set a key, the value from
  ~/.gradle/gradle.properties is shown as effective [I: Gradle precedence; verify for
  your Gradle version].
Detects Fabric (fabric.mod.json, fabric-loom plugin) and prints a one-line "version
matrix" draft for CLAUDE.md (D4): Minecraft, Fabric Loader, Fabric API, Loom, mappings,
Java, Gradle — values only from project files; missing ones are "?" (never guessed).
Suggestions are [I]: verify Loom/Gradle compatibility (esp. configuration cache) in the
Loom/Gradle docs for YOUR versions before changing anything. Nothing is written.

  python gradle_perf.py [PROJECT_DIR]
  python gradle_perf.py --tail-errors run/logs/latest.log   (D3/D5: error/warning blocks only)
  --json   --dry-run (no-op)
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEYS = ["org.gradle.daemon", "org.gradle.parallel", "org.gradle.caching", "org.gradle.jvmargs", "org.gradle.configuration-cache"]


def props(path):
    out = {}
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith(("#", "!")) and ("=" in line or ":" in line):
                k, v = re.split(r"\s*[=:]\s*", line, maxsplit=1)
                out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def analyze(proj):
    proj = Path(proj)
    pp, up = props(proj / "gradle.properties"), props(Path.home() / ".gradle" / "gradle.properties")
    build = read(proj / "build.gradle") + read(proj / "build.gradle.kts")
    settings = read(proj / "settings.gradle") + read(proj / "settings.gradle.kts")
    wrapper = props(proj / "gradle" / "wrapper" / "gradle-wrapper.properties")
    fabric = (proj / "src" / "main" / "resources" / "fabric.mod.json").is_file() or "fabric-loom" in build
    gradle_ver = (re.search(r"gradle-([\d.]+)-", wrapper.get("distributionUrl", "")) or [None, "?"])[1]
    loom = re.search(r"fabric-loom['\"]?\)?\s*version\s*['\"]([^'\"]+)", build) or re.search(r"fabric-loom[^\n]*?['\"]([\d.]+[-\w.]*)['\"]", build + settings)
    m = lambda *ks: next((pp[k] for k in ks if k in pp), "?")
    java = re.search(r"JavaVersion\.VERSION_(\d+)|languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)|release\s*=\s*(\d+)", build)
    matrix = {
        "Minecraft": m("minecraft_version"), "Fabric Loader": m("loader_version"),
        "Fabric API": m("fabric_version", "fabric_api_version"), "Loom": loom.group(1) if loom else m("loom_version"),
        "mappings": m("yarn_mappings", "mappings_version", "parchment_version") if any(k in pp for k in ("yarn_mappings", "mappings_version", "parchment_version")) else ("Mojmap (officialMojangMappings)" if "officialMojangMappings" in build else "?"),
        "Java": next((g for g in (java.groups() if java else []) if g), "?"), "Gradle": gradle_ver,
    }
    cfg = {}
    for k in KEYS:
        src = "~/.gradle" if k in up else ("proje" if k in pp else None)
        cfg[k] = {"value": up.get(k, pp.get(k)), "source": src}
    sugg = []
    if (cfg["org.gradle.daemon"]["value"] or "true").lower() == "false":
        sugg.append(("D1", "org.gradle.daemon=false: her derleme JVM'i yeniden başlatır (gecikme)", "true (varsayılan) [I]"))
    if not cfg["org.gradle.parallel"]["value"]:
        sugg.append(("D1", "org.gradle.parallel ayarsız: çok projeli derlemede paralellik yok", "org.gradle.parallel=true [I]"))
    if not cfg["org.gradle.caching"]["value"]:
        sugg.append(("D1", "org.gradle.caching ayarsız: build cache kapalı", "org.gradle.caching=true [I]"))
    jv = cfg["org.gradle.jvmargs"]["value"] or ""
    mx = re.search(r"-Xmx(\d+)([gGmM])", jv)
    if not mx or (mx.group(2).lower() == "m" and int(mx.group(1)) < 2048) or (mx.group(2).lower() == "g" and int(mx.group(1)) < 2):
        sugg.append(("D1", f"org.gradle.jvmargs bellek düşük/ayarsız ({jv or 'yok'}): Loom/Minecraft için yetersiz olabilir", "ör. -Xmx2G veya üstü [I: makinene göre]"))
    if not cfg["org.gradle.configuration-cache"]["value"]:
        sugg.append(("D1", "configuration-cache ayarsız", "Loom/Gradle sürümün destekliyorsa düşün — ÖNCE Loom belgelerinde doğrula [I]"))
    return {"project": str(proj), "fabric": fabric, "matrix": matrix, "gradle_properties": cfg, "suggestions": sugg,
            "deny_suggestion": ["Read(build/**)", "Read(.gradle/**)", "Read(run/**)", "Read(*.jar)"] if fabric else []}


def tail_errors(path, ctx=2, max_blocks=40):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    hit = re.compile(r"(ERROR|FATAL|Exception|Caused by|FAILURE|WARN|error:|warning:|Mixin .*fail|What went wrong)", re.I)
    keep, blocks = set(), 0
    for i, l in enumerate(lines):
        if hit.search(l):
            blocks += 1
            if blocks > max_blocks:
                break
            keep.update(range(max(0, i - ctx), min(len(lines), i + ctx + 4)))
    out, prev = [], -2
    for i in sorted(keep):
        if i != prev + 1:
            out.append("  ...")
        out.append(lines[i]); prev = i
    return len(lines), out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project", nargs="?", default=".")
    p.add_argument("--tail-errors", metavar="LOG")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    if a.tail_errors:
        n, out = tail_errors(a.tail_errors)
        mt = Path.home() / ".claude" / "skills" / "mintoken" / "scripts" / "filter_log.py"
        print(f"=== {a.tail_errors}: {n} satır → {len(out)} satır (yalnız hata/uyarı blokları) ===")
        print("\n".join(out))
        if mt.is_file():
            print(f"\nMinToken kurulu: tam filtre için `python {mt} {a.tail_errors}` (D3).")
        return 0
    r = analyze(a.project)
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return 0
    print(f"=== {r['project']} — Fabric: {'evet' if r['fabric'] else 'hayır (genel mod)'} ===")
    print("Gradle ayarları (salt okunur):")
    for k, v in r["gradle_properties"].items():
        print(f"  {k} = {v['value'] if v['value'] is not None else '(ayarsız)'}" + (f"  [{v['source']}]" if v["source"] else ""))
    print("Öneriler (hiçbiri uygulanmadı; [I] = sürümüne göre doğrula):")
    for d, issue, s in r["suggestions"] or [("-", "belirgin eksik yok", "-")]:
        print(f"  {d}: {issue} → {s}")
    if r["fabric"]:
        mline = ", ".join(f"{k} {v}" for k, v in r["matrix"].items())
        print(f"\nD4 CLAUDE.md taslağı (onaysız yazılmaz):\n  Sürüm matrisi: {mline}")
        print("D2 doğrulama merdiveni taslağı:\n  Doğrulama: 1) ./gradlew compileJava 2) ilgili test 3) ./gradlew build; runClient/runServer arka planda + çıkış koşulu.")
        print("D6 okuma yasağı önerisi (diff + onayla): " + ", ".join(r["deny_suggestion"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
