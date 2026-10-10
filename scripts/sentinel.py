#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — regression sentinel (`/highper sentinel`, Section N) and escape log
(`/highper escape-log`, O13). Stores ONLY numbers and version/setting labels — never
message text, code or free-text notes — and ONLY in the file you pass with --store.

  template                         print the mini task-set template (references/sentinel-tasks.md)
  add      --store F --task T1 --first-try-pass 1 --fix-rounds 0 --minutes 7.5
           [--interventions 0] [--cache-misses 0]        labels (version/model/effort/style/plugins)
                                                        are filled from pin_check automatically
  compare  --store F --by claude_version|model|effort   n, first-try rate, fix rounds, minutes;
                                                        <3 runs or difference inside noise → "değişiklik görülmedi"
  escape   --store F --gate G --cls C --would-catch W   record an escape (bug found after delivery)
  escapes  --store F                                    escape rate in Q1 language (rule of three)
  --dry-run   print the record instead of writing it
"""
import argparse
import datetime
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pin_check  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GATES = ["compile", "test", "review", "scope_guard", "diff_audit", "canary", "verify_gate", "human", "none"]
CLASSES = ["logic", "api_version", "scope", "test_weakened", "regression", "config", "other"]


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"runs": [], "escapes": []}


def save(path, data, dry):
    if dry:
        print(json.dumps(data["runs"][-1:] or data["escapes"][-1:], indent=1, ensure_ascii=False)); print(f"[dry-run] {path} yazılmadı.")
        return
    Path(path).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Kaydedildi: {path}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("template")
    ad = sub.add_parser("add")
    ad.add_argument("--store", required=True); ad.add_argument("--task", required=True)
    ad.add_argument("--first-try-pass", type=int, choices=[0, 1], required=True)
    ad.add_argument("--fix-rounds", type=int, required=True); ad.add_argument("--minutes", type=float, required=True)
    ad.add_argument("--interventions", type=int, default=0); ad.add_argument("--cache-misses", type=int, default=0)
    cp = sub.add_parser("compare"); cp.add_argument("--store", required=True)
    cp.add_argument("--by", default="claude_version", choices=["claude_version", "model", "effort", "output_style"])
    es = sub.add_parser("escape"); es.add_argument("--store", required=True)
    es.add_argument("--gate", choices=GATES, required=True); es.add_argument("--cls", choices=CLASSES, required=True)
    es.add_argument("--would-catch", choices=GATES + ["hook", "claude_md"], required=True)
    el = sub.add_parser("escapes"); el.add_argument("--store", required=True)
    for sp in (ad, es):
        sp.add_argument("--dry-run", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    if a.cmd == "template" or a.cmd is None:
        ref = Path(__file__).resolve().parent.parent / "references" / "sentinel-tasks.md"
        print(ref.read_text(encoding="utf-8") if ref.is_file() else "references/sentinel-tasks.md bulunamadı")
        return 0
    data = load(a.store)
    if a.cmd == "add":
        st = pin_check.current_state()
        rec = {"date": datetime.date.today().isoformat(), "claude_version": st["claude_version_latest"], "model": st["model"],
               "effort": st["effort"], "effort_source": st["effort_source"], "output_style": st["output_style"],
               "plugins": st["plugins"], "task_id": a.task, "first_try_pass": a.first_try_pass, "fix_rounds": a.fix_rounds,
               "minutes": a.minutes, "interventions": a.interventions, "cache_misses": a.cache_misses}
        data["runs"].append(rec); save(a.store, data, a.dry_run); return 0
    if a.cmd == "escape":
        data["escapes"].append({"date": datetime.date.today().isoformat(), "gate_passed": a.gate, "class": a.cls,
                                "would_catch": a.would_catch, "claude_version": pin_check.current_state()["claude_version_latest"]})
        save(a.store, data, a.dry_run)
        same = sum(1 for e in data["escapes"] if e["class"] == a.cls)
        if same >= 2:
            print(f"O13: '{a.cls}' sınıfı {same} kez kaçtı → yeni kapı ÖNERİSİ: {a.would_catch} (onayla eklenir).")
        return 0
    if a.cmd == "escapes":
        n, k = len(data["runs"]), len(data["escapes"])
        print(f"Teslim (kayıtlı koşu) {n}, kaçak {k}.")
        if n:
            if k == 0:
                print(f"Q1: {n} tesliminde 0 kaçak görüldü; %95 güvenle üst sınır ≈ 3/{n} ≈ %{300 / n:.1f} [I: üç kuralı] — \"sıfır risk\" değildir.")
            else:
                print(f"Kaçak oranı {k}/{n} = %{100 * k / n:.1f}; küçük örneklemde güven aralığı geniştir.")
        by = defaultdict(int)
        for e in data["escapes"]:
            by[(e["gate_passed"], e["class"])] += 1
        for (g, c), v in sorted(by.items(), key=lambda x: -x[1]):
            print(f"  geçtiği kapı {g}, sınıf {c}: {v}")
        return 0
    if a.cmd == "compare":
        groups = defaultdict(list)
        for r in data["runs"]:
            groups[str(r.get(a.by))].append(r)
        if not groups:
            print("Kayıt yok."); return 0
        print(f"=== Karşılaştırma: {a.by} ===\n  grup                         n  ilk_deneme  düzeltme  dk")
        rates = {}
        for g, rs in groups.items():
            n = len(rs); fp = sum(r["first_try_pass"] for r in rs) / n
            rates[g] = (fp, n)
            print(f"  {g[:28]:<28} {n:>2}  {fp:>10.2f}  {sum(r['fix_rounds'] for r in rs) / n:>8.2f}  {sum(r['minutes'] for r in rs) / n:>4.1f}")
        if len(rates) >= 2:
            (g1, (p1, n1)), (g2, (p2, n2)) = list(rates.items())[:2]
            noise = 2.8 * math.sqrt(max(0.25, (p1 + p2) / 2 * (1 - (p1 + p2) / 2)) * (1 / n1 + 1 / n2))
            if min(n1, n2) < 3 or abs(p1 - p2) < noise:
                print(f"Sonuç: değişiklik görülmedi (fark {abs(p1 - p2):.2f} < gürültü ≈{noise:.2f} veya <3 tekrar) — N4.")
            else:
                print(f"Sonuç: ilk-deneme oranı farkı {p1 - p2:+.2f} gürültünün (≈{noise:.2f}) üstünde — yine de 'işaret', tek görev seti.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
