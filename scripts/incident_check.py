#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — "regime change suspect" diagnosis (`/highper why-slow`, J-1/J-2). READ-ONLY.

When quality or speed drops suddenly, checks in order:
  (1) did `claude --version` change (vs. an optional pin snapshot)   (2) which model/alias
  (3) effort value and its source   (4) plugins / output style   (5) suggests a
  `claude --safe-mode` re-run   (6) cache-miss signs in recent sessions (cache writes after
  the first request)   (7) is the problem in long/idle sessions (K1-2 symptom)
  (8) random pass/fail of the same prompt → K2-3 class: retry, /feedback.
J-2: lists your session dates that fall inside the incident windows documented by
Anthropic (references/known-incidents.md). Only counters/dates are read; no message text.

  --pins FILE   compare with a pin_check.py snapshot     --json   --dry-run (no-op)
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perf_baseline  # noqa: E402
import pin_check  # noqa: E402
from audit_perf import claude_home  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INCIDENTS = [  # [D] anthropic.com/engineering, verified 2026-10-10
    ("K1 Claude Code kalite kaybı (effort high→medium, boşta oturumda düşünme temizleme hatası, ayrıntı sınırı)", "2026-03-04", "2026-04-20", "v2.1.116 ile çözüldü"),
    ("K2 API altyapı hataları (bağlam yönlendirme, çıktı bozulması, top-k)", "2025-08-05", "2025-09-16", "Sonnet 4 / Opus 4.x / Haiku 3.5"),
]


def cache_miss_signs(path):
    """Count requests (after the first) whose cache writes exceed 50% of input-side tokens."""
    n, seen, first = 0, set(), True
    with open(perf_baseline.lp(path), encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            if '"assistant"' not in raw:
                continue
            try:
                m = json.loads(raw).get("message") or {}
            except ValueError:
                continue
            if not m.get("id") or m["id"] in seen:
                continue
            seen.add(m["id"])
            u = m.get("usage") or {}
            tot = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            if first:
                first = False
                continue
            if tot > 20000 and (u.get("cache_creation_input_tokens") or 0) > 0.5 * tot:
                n += 1
    return n


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pins"); p.add_argument("--home"); p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    home = claude_home(a.home)
    st = pin_check.current_state(home)
    base = perf_baseline.baseline(home / "projects", last=5)
    root = home / "projects"
    recent = sorted(root.glob("*/*.jsonl"), key=perf_baseline.mtime, reverse=True)[:5]
    misses = {f.stem[:8]: cache_miss_signs(f) for f in recent}
    switches = pin_check.recent_model_switches(home)
    windows = []
    for f in root.glob("*/*.jsonl"):
        d = datetime.date.fromtimestamp(perf_baseline.mtime(f)).isoformat()
        for name, start, end, note in INCIDENTS:
            if start <= d <= end:
                windows.append((f.stem[:8], d, name))
    changed = {}
    if a.pins:
        old = json.loads(Path(a.pins).read_text(encoding="utf-8"))
        changed = {k: (old.get(k), st.get(k)) for k in ("claude_version_latest", "model", "effort", "output_style", "plugins") if old.get(k) != st.get(k)}
    r = {"state": st, "changed_since_pin": changed, "cache_miss_signs": misses, "model_switches": switches,
         "idle_gaps_over_1h": base["total"].get("idle_gaps_over_1h", 0), "incident_overlap": windows}
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return 0
    print("=== HighPer why-slow (J-1) ===")
    print(f"(1) Claude Code: {', '.join(st['claude_versions']) or 'bulunamadı'}" + (f" — pin'den beri değişti: {changed['claude_version_latest']}" if "claude_version_latest" in changed else ""))
    print(f"(2) model: {st['model']} [{st['model_source']}] — /model ve /status ile çözülen sürümü doğrula")
    print(f"(3) effort: {st['effort']} [{st['effort_source']}] (çözüm sırası: açık seçim → kayıtlı ayar → model varsayılanı [D])")
    print(f"(4) çıktı stili: {st['output_style']}; eklentiler: {', '.join(st['plugins']) or '-'}" + (f"; pin'den beri değişen: {', '.join(k for k in changed if k != 'claude_version_latest')}" if changed else ""))
    print("(5) temiz taban: aynı görevi `claude --safe-mode` ile dene (CLAUDE.md, skill, eklenti, hook, MCP, otomatik bellek kapalı) [D]")
    print("(6) önbellek ıskası işaretleri (ilk istekten sonra yazımın >%50 olduğu istek): " + ", ".join(f"{k} {v}" for k, v in misses.items()) +
          " — /usage 'Prompt cache (main)' satırındaki olası nedenle doğrula [D]")
    for s in switches:
        if s["switches"]:
            print(f"    oturum {s['session']}: {s['switches']} model geçişi ({', '.join(s['models'])}) — otomatik yedek model olabilir [D]")
    print(f"(7) son oturumlarda 1 saatten uzun boşluk sonrası devam: {r['idle_gaps_over_1h']} — belirti unutkanlık/tekrar ise /clear veya yeni oturum (K1-2)")
    print("(8) aynı istem bir geçip bir kalıyorsa (K2-3 sınıfı) istemci tarafı çözüm olmayabilir: tekrar dene; tekrarlanabilir örnekle /feedback [D]")
    if windows:
        print("J-2 belgelenmiş olay pencerelerine düşen oturumlar: " + ", ".join(f"{s} ({d})" for s, d, _ in windows[:8]))
    else:
        print("J-2 hiçbir oturum belgelenmiş olay pencerelerine (K1: 2026-03-04→04-20, K2: 2025-08-05→09-16) düşmüyor.")
    print("Yeni olaylar: anthropic.com/engineering ve status sayfası (WebFetch ile kullanıcı onayıyla); bulunamazsa \"doğrulanamadı\".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
