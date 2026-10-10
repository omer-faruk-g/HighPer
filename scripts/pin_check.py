#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — version / model / effort / settings pinning (O9). Read-only by default.

Shows the current state: installed Claude Code version(s), configured model, effort and
WHERE it comes from (resolution: explicit choice → saved setting → model default [D]),
output style, enabled plugins, fallback model, auto-compact window, and model switches
seen inside recent sessions (an automatic fallback is a model change [D]).
  --snapshot FILE   write the state as JSON to FILE (only to the path you give)
  --compare FILE    compare the current state with a snapshot; changed fields = profile broken (O9)
  --json   --dry-run (no-op unless --snapshot, then prints instead of writing)
Model-switch guard: a PreModelSwitch hook (v2.1.251+, exit 2 blocks the switch, matcher on
the canonical model name) can require confirmation; it does NOT run for automatic fallback —
those reach PostModelSwitch only [D: hooks, verified 2026-10-10]. HighPer only suggests it.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_perf import claude_home, installed_plugins, load_sources, lookup  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def claude_versions():
    vers = set()
    exe = shutil.which("claude")
    if exe:
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20).stdout
            m = re.search(r"(\d+\.\d+\.\d+)", out)
            if m:
                vers.add(m.group(1))
        except (OSError, subprocess.SubprocessError):
            pass
    bases = [Path(os.environ.get("APPDATA", "")) / "Claude" / "claude-code", Path.home() / ".local" / "share" / "claude" / "versions"]
    bases += list((Path.home() / "AppData" / "Local" / "Packages").glob("Claude_*/LocalCache/Roaming/Claude/claude-code"))  # MSIX desktop app
    for base in bases:
        if base.is_dir():
            vers.update(p.name for p in base.iterdir() if re.fullmatch(r"\d+\.\d+\.\d+", p.name))
    key = lambda v: tuple(int(x) for x in v.split("."))
    return sorted(vers, key=key)


def recent_model_switches(home, n=3):
    root = home / "projects"
    files = sorted(root.glob("*/*.jsonl"), key=lambda p: os.stat("\\\\?\\" + os.path.abspath(str(p)) if os.name == "nt" else p).st_mtime, reverse=True)[:n]
    res = []
    for f in files:
        models, prev, switches = [], None, 0
        try:
            fh = open("\\\\?\\" + os.path.abspath(str(f)) if os.name == "nt" else f, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                if '"assistant"' not in raw:
                    continue
                try:
                    m = (json.loads(raw).get("message") or {}).get("model")
                except ValueError:
                    continue
                if m and not m.startswith("<"):
                    if prev and m != prev:
                        switches += 1
                    if m not in models:
                        models.append(m)
                    prev = m
        res.append({"session": f.stem[:8], "models": models, "switches": switches})
    return res


def current_state(home=None, cwd=None, environ=None):
    home = home or claude_home(); cwd = cwd or Path(os.getcwd()); environ = environ if environ is not None else dict(os.environ)
    srcs = load_sources(home, cwd)
    first = lambda k: (lookup(k, srcs, environ) or [(None, None)])[-1]
    vers = claude_versions()
    model_src, model = first("ANTHROPIC_MODEL") if lookup("ANTHROPIC_MODEL", srcs, environ) else first("model")
    eff_src, eff = first("CLAUDE_CODE_EFFORT_LEVEL") if lookup("CLAUDE_CODE_EFFORT_LEVEL", srcs, environ) else first("effortLevel")
    return {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "claude_versions": vers, "claude_version_latest": vers[-1] if vers else None,
        "model": model or "default (Opus 5.5 on Pro/Max/Team/Enterprise/API [D: model-config])", "model_source": model_src or "default",
        "effort": eff or "model default (/effort or picker may override per model)", "effort_source": eff_src or "model default",
        "output_style": first("outputStyle")[1] or "default", "fallbackModel": first("fallbackModel")[1],
        "autoCompactWindow": first("autoCompactWindow")[1], "fastMode": first("fastMode")[1],
        "plugins": sorted(p["name"] for p in installed_plugins(home) if p["enabled"]),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--snapshot"); p.add_argument("--compare"); p.add_argument("--home"); p.add_argument("--cwd")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    home = claude_home(a.home)
    st = current_state(home, Path(a.cwd or os.getcwd()))
    sw = recent_model_switches(home)
    if a.snapshot:
        if a.dry_run:
            print(json.dumps(st, indent=1, ensure_ascii=False)); print(f"[dry-run] {a.snapshot} yazılmadı."); return 0
        Path(a.snapshot).write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Durum kaydedildi: {a.snapshot}"); return 0
    if a.compare:
        old = json.loads(Path(a.compare).read_text(encoding="utf-8"))
        changed = {k: (old.get(k), st.get(k)) for k in st if k not in ("date",) and old.get(k) != st.get(k)}
        if a.json:
            print(json.dumps({"changed": changed}, indent=1, ensure_ascii=False)); return 0
        print(f"=== {a.compare} ({old.get('date')}) → şimdi ===")
        for k, (o, n) in changed.items():
            print(f"  DEĞİŞTİ {k}: {o} → {n}")
        print("  değişiklik yok" if not changed else "\nO9: sabitlenmiş durum değişti → Sıfır Tolerans profili bozulmuş sayılır; görevi yeniden doğrula.")
        return 0
    if a.json:
        print(json.dumps({"state": st, "recent_sessions": sw}, indent=1, ensure_ascii=False)); return 0
    print("=== Şu anki durum (O9) ===")
    for k, v in st.items():
        print(f"  {k}: {v}")
    print("Son oturumlarda model geçişi (otomatik yedek model dahil — önbellek soğur, kalite değişebilir):")
    for s in sw:
        print(f"  {s['session']}: modeller {', '.join(s['models']) or '-'}; oturum içi geçiş {s['switches']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
