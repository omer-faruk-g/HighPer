#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — model router (`/highper route`, Section L). Produces a SUGGESTION only;
never changes the model, effort or any setting.

Score the task on 5 axes, each 0–2 (0 = easy/safe, 2 = hard/risky):
  --ambiguity      requirement clarity (0 net … 2 belirsiz)
  --scope          files/modules, client/server split, backward compat (0 tek dosya … 2 geniş)
  --verifiability  can compile/test verify it fast? (0 hızlı doğrulanır … 2 doğrulaması zor)
  --risk           cost of a mistake: live server, data loss (0 düşük … 2 yüksek)
  --novelty        similar example in the codebase? (0 var … 2 yok)
Line count is NOT used: the docs give no line threshold, and 100 lines of mixin/concurrency
can be harder than 1,000 lines of mechanical rename [I].
The scoring and thresholds are HighPer's proposal [I]; only the model roles are [D].

  python route_model.py --ambiguity 1 --scope 0 --verifiability 0 --risk 0 --novelty 0
  --json   --dry-run (no-op)
"""
import argparse
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TIERS = [
    (0, 3, "Sonnet, effort low/medium; mekanik yan işler (log özeti, arama, test çalıştırma) Haiku alt-ajanında [D: costs]",
     "tek turda kaçırılan kenar durum olasılığı → G2/G7 doğrulaması şart"),
    (4, 6, "Sonnet high veya Opus medium; G1+G2+G7, riskliyse G3",
     "orta; Opus 5.5 medium ≈/≥ Opus 5 high [D: model-config] → önce 'aynı model, doğru effort'"),
    (7, 10, "Opus high/xhigh + plan modu (opusplan: plan Opus, uygulama Sonnet [D]); G1–G7",
     "yüksek token/süre; G7 yine istenir"),
]
RULES = [
    "(a) Modeli GÖREV BAŞINDA seç: /model ve çoğu modelde effort değişimi önbelleği bozar; opusplan her plan geçişinde model değişimi; skill/komut frontmatter'ında farklı model o tur için model değişimidir [D: prompt-caching].",
    "(b) Alt-ajan model/effort'unu frontmatter ile işe uydur; ana model Opus ise alt-ajanlar Opus'u miras alır (pahalı) [D: costs].",
    "(c) Alt-ajan kendi modelinin bağlam penceresini kullanır; düşünme ayarını ana konuşmadan miras alır [D: sub-agents].",
    "(d) Otomatik yedek model (güvenlik sınıflandırıcısı yönlendirmesi) bir model değişimidir: önbellek soğur, kalite farkı olabilir [D].",
    "(e) Opus 5.5 medium, Opus 5 high'a eşit/üstün → önce aynı model + doğru effort [D].",
    "(f) Abonelikte model ailesi limitleri ayrı; Opus limiti dolunca başka aile çalışmayı sürdürür [D: costs].",
]


def route(scores):
    total = sum(scores.values())
    tier = next(t for t in TIERS if t[0] <= total <= t[1])
    return {"scores": scores, "total": total, "suggestion": tier[2], "tradeoff": tier[3], "label": "[I] HighPer önerisi; model rolleri [D]"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for ax in ("ambiguity", "scope", "verifiability", "risk", "novelty"):
        p.add_argument(f"--{ax}", type=int, choices=[0, 1, 2])
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    scores = {ax: getattr(a, ax) for ax in ("ambiguity", "scope", "verifiability", "risk", "novelty")}
    missing = [k for k, v in scores.items() if v is None]
    if missing:
        print("Eksik eksen puanı: " + ", ".join(missing) + " (her biri 0–2; açıklama için --help)")
        return 2
    r = route(scores)
    if a.json:
        print(json.dumps({**r, "rules": RULES}, indent=1, ensure_ascii=False)); return 0
    print(f"Puanlar: {scores} → toplam {r['total']}/10  {r['label']}")
    print(f"ÖNERİ: {r['suggestion']}\nTakas: {r['tradeoff']}")
    print("Kurallar:\n  " + "\n  ".join(RULES))
    print("Kanıt kuralı: kendi görev setinde iki modeli aynı görevde (aynı effort, ≥3 tekrar) karşılaştırmadan \"Sonnet yeter\" denmez (sentinel.py compare --by model).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
