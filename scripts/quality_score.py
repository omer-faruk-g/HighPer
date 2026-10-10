#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — quality metrics from YOUR task records (I1–I3, Q1–Q3). Read-only.

Input: CSV or JSON records you fill in (one row per task run), columns/keys:
  condition, task_id, first_try_pass (0/1), criteria_met (0..1), fix_rounds,
  interventions, reviewer_real_bugs, minutes, escaped (0/1, optional: bug found later)
Output per condition: n, first-try-pass rate, mean criteria_met, mean fix rounds,
mean interventions, reviewer bugs, mean minutes, escapes — reported SEPARATELY (Q3).
  --weights a=..,b=..,c=..,d=..  optional composite: formula and weights are printed (I1)
  --compare BEFORE AFTER          change per metric + "2×" check with ceiling warning (I2)
  --min-detectable N [--p P]      smallest difference detectable with N tasks per arm (Q2)
  --escapes K --deliveries N      escape-rate report in Q1 language (rule of three)
No savings/quality percentage is ever promised; small samples are called "işaret, kanıt değil".

  python quality_score.py records.csv --compare baseline highper
  python quality_score.py --min-detectable 10
  python quality_score.py --escapes 0 --deliveries 40
  --json   --dry-run (no-op)
"""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METRICS = ["first_try_pass", "criteria_met", "fix_rounds", "interventions", "reviewer_real_bugs", "minutes", "escaped"]


def load(path):
    if path.lower().endswith(".json"):
        rows = json.load(open(path, encoding="utf-8"))
    else:
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []
    for r in rows:
        rec = {"condition": str(r.get("condition", "?")), "task_id": str(r.get("task_id", "?"))}
        for m in METRICS:
            v = r.get(m)
            rec[m] = float(v) if v not in (None, "") else None
        out.append(rec)
    return out


def summarize(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    res = {}
    for c, rs in by.items():
        s = {"n": len(rs)}
        for m in METRICS:
            vals = [r[m] for r in rs if r[m] is not None]
            s[m] = round(sum(vals) / len(vals), 3) if vals else None
        res[c] = s
    return res


def rule_of_three(n):
    return 3.0 / n if n else None


def mde(n, p):
    """Approx. minimum detectable difference between two proportions (alpha .05 two-sided, power .8)."""
    return 2.8 * math.sqrt(2 * p * (1 - p) / n) if n else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("records", nargs="?")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--weights")
    ap.add_argument("--min-detectable", type=int, metavar="N")
    ap.add_argument("--p", type=float, default=0.5, help="expected base rate for --min-detectable (default 0.5 = worst case)")
    ap.add_argument("--escapes", type=int); ap.add_argument("--deliveries", type=int)
    ap.add_argument("--json", action="store_true"); ap.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = ap.parse_args(argv)
    out = {}
    if a.min_detectable:
        d = mde(a.min_detectable, a.p)
        out["min_detectable"] = d
        if not a.json:
            print(f"Q2: kol başına {a.min_detectable} görevle (taban oran {a.p:.0%}) görebileceğin en küçük fark ≈ {d:.0%} [I: normal yaklaşım, α=0,05, güç=0,8].")
            print(f"    Bir görev = %{100 / a.min_detectable:.1f}. Daha küçük farkı görmek için çok daha fazla görev gerekir.")
    if a.escapes is not None and a.deliveries:
        ub = rule_of_three(a.deliveries) if a.escapes == 0 else None
        out["escape_rate"] = a.escapes / a.deliveries
        if not a.json:
            if a.escapes == 0:
                print(f"Q1: {a.deliveries} tesliminde 0 kaçak görüldü; %95 güvenle üst sınır ≈ 3/{a.deliveries} ≈ %{ub * 100:.1f} [I: üç kuralı]. Bu \"sıfır risk\" DEĞİLDİR.")
                print(f"    10⁻⁷ (%0,00001) iddiası için ≈ 30.000.000 kaçaksız bağımsız teslim gerekir.")
            else:
                print(f"Q1: {a.deliveries} tesliminde {a.escapes} kaçak (oran %{a.escapes / a.deliveries * 100:.1f}); küçük örneklem → güven aralığı geniş.")
    if a.records:
        rows = load(a.records)
        s = summarize(rows)
        out["summary"] = s
        if not a.json:
            print("=== I1 metrikleri (koşul başına; tek sayıya indirgenmez) ===")
            print("  koşul        n  ilk_deneme  ölçüt  düzeltme  müdahale  inceleme_hata  dk    kaçak")
            for c, v in s.items():
                f = lambda k: "-" if v[k] is None else f"{v[k]:.2f}"
                print(f"  {c:<11} {v['n']:>2}  {f('first_try_pass'):>10}  {f('criteria_met'):>5}  {f('fix_rounds'):>8}  {f('interventions'):>8}  {f('reviewer_real_bugs'):>13}  {f('minutes'):>4}  {f('escaped'):>5}")
            small = [c for c, v in s.items() if v["n"] < 5]
            if small:
                print(f"  Örneklem küçük ({', '.join(small)} < 5 görev): sonuçlar \"işaret, kanıt değil\" (I3).")
        if a.weights:
            w = {k: float(v) for k, v in (x.split("=") for x in a.weights.split(","))}
            keys = {"a": "first_try_pass", "b": "criteria_met", "c": "fix_rounds", "d": "interventions"}
            print(f"\nBirleşik skor formülü (ağırlıkları SEN seçtin): skor = {w.get('a', 0)}·ilk_deneme + {w.get('b', 0)}·ölçüt − {w.get('c', 0)}·düzeltme − {w.get('d', 0)}·müdahale")
            for c, v in s.items():
                sc = sum((1 if k in "ab" else -1) * w.get(k, 0) * (v[m] or 0) for k, m in keys.items())
                print(f"  {c}: {sc:.3f}")
        if a.compare:
            b, af = s.get(a.compare[0]), s.get(a.compare[1])
            if not b or not af:
                print(f"\nKarşılaştırma için koşul bulunamadı: {a.compare}"); return 1
            print(f"\n=== {a.compare[0]} → {a.compare[1]} (ölçülen değişim) ===")
            for m in METRICS:
                if b[m] is not None and af[m] is not None:
                    print(f"  {m}: {b[m]:.2f} → {af[m]:.2f}")
            base = b["first_try_pass"]
            if base is not None:
                if base >= 0.5:
                    print(f"  2× tavanı: taban ilk-deneme oranı {base:.0%} ≥ %50 → bu metrikte 2 kat matematiksel olarak imkânsız; \"hata oranının yarıya inmesi\" (1−oran) daha anlamlı hedef (I2).")
                elif af["first_try_pass"] is not None and base > 0:
                    print(f"  2× sınaması: {base:.2f} → {af['first_try_pass']:.2f} = {af['first_try_pass'] / base:.2f}× (yalnız bu görev setinde; tekrar sayısı ve gürültüye bak).")
            if min(b["n"], af["n"]) < 3:
                print("  Uyarı: koşul başına <3 tekrar — istatistik değildir (Bölüm E3).")
    if not out:
        ap.print_help(); return 2
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
