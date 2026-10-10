#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — CLAUDE.md / MEMORY.md lint (READ-ONLY). H12, H50, H67, F6, G10, D2, D4.

Checks every instruction file Claude Code would load for the project (user CLAUDE.md,
every CLAUDE.md / CLAUDE.local.md / .claude/CLAUDE.md from the filesystem root down to
the project) — or only the files you pass:
  - size: >200 lines warning [D: memory], MEMORY.md >200 lines / >25 KB [D]
  - no runnable verification command (build/test) [D: best-practices "Provide verification"]
  - vague, unverifiable wording ("düzgün", "temiz kod", "best practices", "properly" ...)
  - contradictions: "always/never/her zaman/asla X" pairs on the same subject
  - IMPORTANT/ÖNEMLİ overuse (>3: emphasis stops standing out) [D: best-practices]
  - content that should be left out: long code/API dumps, file-by-file tours [D: H67]
  - missing "Compact Instructions" section [D: H50]
  - possibly stale lines: dates older than 6 months, "TODO", "temporary/geçici"
Findings are ranked (correctness first). Nothing is ever written.

  python claude_md_lint.py [FILE ...] [--cwd DIR] [--home DIR] [--json] [--dry-run]
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VAGUE = re.compile(r"\b(properly|clean code|best practices?|good code|as needed|appropriate(ly)?|düzgün(ce)?|temiz kod|iyi (bir )?kod|gerektiği gibi|uygun şekilde|en iyi uygulama)\b", re.I)
VERIFY = re.compile(r"(gradlew|gradle\s|mvn|npm (run )?(test|build)|pytest|go test|cargo (test|build)|make\b|dotnet (test|build)|tsc\b|ruff|eslint|compileJava)", re.I)
RULE = re.compile(r"\b(always|never|must not|must|do not|don't|her zaman|asla|kesinlikle|yapma|kullanma|kullan)\b", re.I)
NEG = re.compile(r"\b(never|must not|do not|don't|asla|yapma|kullanma)\b", re.I)
DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")


def candidate_files(home, cwd):
    files = [home / "CLAUDE.md"]
    cur = cwd.resolve()
    for d in list(reversed([cur] + list(cur.parents))):
        files += [d / "CLAUDE.md", d / "CLAUDE.local.md", d / ".claude" / "CLAUDE.md"]
    if not any(f.is_file() for f in files[1:]):
        files.append(cwd / "AGENTS.md")  # read only when no CLAUDE.md [D: H12]
    out, seen = [], set()
    for f in files:
        if f.is_file() and f.resolve() not in seen:
            seen.add(f.resolve()); out.append(f)
    return out


def subject(line):
    words = re.findall(r"[\wçğıöşü./`-]{3,}", NEG.sub(" ", RULE.sub(" ", line.lower())))
    return " ".join(words[:4])


def lint_file(path, user_level=False):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    f = []
    is_memory = path.name.upper() == "MEMORY.MD"
    if is_memory and (len(lines) > 200 or len(text.encode()) > 25 * 1024):
        f.append((2, "boyut", f"MEMORY.md {len(lines)} satır / {len(text.encode()) // 1024} KB: yalnız ilk 200 satır/25 KB yüklenir [D]", None))
    elif len(lines) > 200:
        f.append((2, "boyut", f"{len(lines)} satır (>200): kurallar unutulabilir; budama testi uygula (H67) [D]", None))
    if not is_memory and not user_level and not VERIFY.search(text):
        f.append((1, "doğrulama", "çalıştırılabilir doğrulama komutu yok (ör. `./gradlew compileJava`) — Claude 'bitti'yi kontrol edemez (H15/G7)", None))
    if not is_memory and not user_level and not re.search(r"compact instructions|sıkıştırma talimat", text, re.I):
        f.append((3, "sıkıştırma", "'Compact Instructions' bölümü yok: sıkıştırmada değişen dosya listesi/doğrulama komutları korunsun diye ekle (H50) [D]", None))
    emph = [i + 1 for i, l in enumerate(lines) if re.search(r"\b(IMPORTANT|ÖNEMLİ|CRITICAL|MUST)\b", l)]
    if len(emph) > 3:
        f.append((3, "vurgu", f"{len(emph)} satırda IMPORTANT/ÖNEMLİ: çoğuna eklenirse hiçbiri öne çıkmaz [D]", emph[:6]))
    rules = {}
    in_code, code_len = False, 0
    cutoff = datetime.date.today() - datetime.timedelta(days=183)
    for i, l in enumerate(lines, 1):
        if l.strip().startswith("```"):
            if in_code and code_len > 25:
                f.append((3, "dışarıda bırak", f"{code_len} satırlık kod/API bloğu: uzun dokümanı bağlantıyla ver (H67) [D]", [i]))
            in_code, code_len = not in_code, 0
            continue
        if in_code:
            code_len += 1
            continue
        if VAGUE.search(l):
            f.append((2, "belirsiz", "doğrulanamaz ifade: komut veya ölçüt yaz (ör. '`./gradlew build` ile doğrula')", [i]))
        if RULE.search(l):
            subj = subject(l)
            if subj:
                pol = bool(NEG.search(l))
                if subj in rules and rules[subj][0] != pol:
                    f.append((1, "çelişki", f"satır {rules[subj][1]} ile çelişiyor olabilir (aynı konu, zıt yön)", [rules[subj][1], i]))
                rules.setdefault(subj, (pol, i))
        m = DATE.search(l)
        if m:
            try:
                if datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) < cutoff:
                    f.append((3, "eski", "6 aydan eski tarihli satır: hâlâ geçerli mi?", [i]))
            except ValueError:
                pass
        if re.search(r"\b(TODO|FIXME|temporary|geçici)\b", l, re.I):
            f.append((3, "eski", "geçici/TODO satırı kalıcı talimatta", [i]))
    tour = sum(1 for l in lines if re.match(r"^\s*[-*]\s*`?[\w./-]+\.(java|py|ts|js|kt|gradle|json)`?\s*[:—-]", l))
    if tour > 10:
        f.append((3, "dışarıda bırak", f"{tour} satır dosya-dosya tarif: koddan çıkarılabilir, sil (H67) [D]", None))
    return {"file": str(path), "lines": len(lines), "findings": sorted(f, key=lambda x: x[0])}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="*"); p.add_argument("--cwd"); p.add_argument("--home")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    home = Path(a.home) if a.home else Path.home() / ".claude"
    files = [Path(x) for x in a.files] if a.files else candidate_files(home, Path(a.cwd or os.getcwd()))
    mem = sorted((home / "projects").glob("*/memory/MEMORY.md"), key=lambda q: q.stat().st_size, reverse=True)[:1] if not a.files else []
    results = [lint_file(f, user_level=(f.resolve() == (home / 'CLAUDE.md').resolve())) for f in files + mem if f.is_file()]
    if not a.files and not any(r['file'] != str(home / 'CLAUDE.md') and not r['file'].upper().endswith('MEMORY.MD') for r in results):
        results.append({'file': '(proje CLAUDE.md yok)', 'lines': 0, 'findings': [(1, 'doğrulama', 'proje CLAUDE.md yok: kısa bir dosya + doğrulama komutu + Compact Instructions önerilir (H12/H15/H50)', None)]})
    if a.json:
        print(json.dumps(results, indent=1, ensure_ascii=False)); return 0
    if not results:
        print("Talimat dosyası bulunamadı (CLAUDE.md yok). Öneri: kısa bir CLAUDE.md + doğrulama komutu (H12/H15)."); return 0
    sev = {1: "doğruluk", 2: "güvenilirlik", 3: "bakım"}
    for r in results:
        print(f"=== {r['file']} ({r['lines']} satır) ===")
        if not r["findings"]:
            print("  bulgu yok")
        for s, kind, msg, where in r["findings"]:
            loc = f" (satır {', '.join(map(str, where))})" if where else ""
            print(f"  [{sev[s]}] {kind}: {msg}{loc}")
    print("\nHiçbir dosya değiştirilmedi. Düzeltmeleri diff + açık onayla uygula (İlke 5).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
