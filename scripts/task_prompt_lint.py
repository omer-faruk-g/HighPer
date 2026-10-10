#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — task prompt lint (READ-ONLY). H15, H60, H61, G1, G11.

Checks a task prompt for: success criterion, runnable verification command, scope,
do-not-touch list, reference to an existing pattern, pointer to a source, symptom
description (bug work), root-cause request, and suggests a task class XS/S/M/L.
The prompt text is analysed locally and never stored or sent anywhere.

  python task_prompt_lint.py "Fabric modda yeni event handler ekle ..."
  python task_prompt_lint.py --file istem.txt        echo "..." | python task_prompt_lint.py -
  --json   --dry-run (no-op)
"""
import argparse
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECKS = [
    ("başarı ölçütü", r"(geçmeli|geçsin|başarılı|0 ile çık|exit 0|pass(es)?\b|should\b|expected|beklenen|bitti say|done when|kabul ölçüt|acceptance)",
     "'bitti'nin nasıl kontrol edileceğini yaz (ör. \"./gradlew compileJava 0 ile çıkmalı\")", "H15"),
    ("doğrulama komutu", r"(`[^`]*(gradlew|gradle|mvn|npm|pytest|go test|cargo|make|test)[^`]*`|\./gradlew|\bpytest\b|npm (run )?test)",
     "çalıştırılabilir komut ver (ör. `./gradlew test --tests '*Handler*'`)", "H59/G7"),
    ("kapsam", r"(\b[\w/-]+\.(java|kt|py|ts|js|json|gradle|sk|yml)\b|src/|sadece|yalnız|only\b|şu dosya|this file)",
     "hangi dosya/dizin/senaryo olduğunu yaz", "H61"),
    ("dokunulmayacaklar", r"(dokunma|değiştirme|elleme|don't touch|do not (modify|change|touch)|hariç|yasak)",
     "dokunulmayacak dosyaları yaz (build/, run/, gradle/wrapper/, canlı sunucu)", "O3/G1"),
    ("mevcut kalıp", r"(gibi yaz|örnek al|like\b|mevcut kalıp|existing pattern|benzer şekilde|aynı şekilde)",
     "örnek dosya ver (\"X.java gibi yaz; yeni kütüphane ekleme\")", "H61"),
    ("kaynak işaretçisi", r"(git (log|geçmiş|history)|dependencies|jar\b|dokümantasyon|docs?\b|kaynağa bak|source)",
     "bilginin kaynağını göster (git geçmişi, gradle dependencies, jar)", "H61/G5"),
]
BUG = re.compile(r"(hata|bug|crash|çök|exception|stack ?trace|error|çalışmıyor|broken|fail)", re.I)
SYMPTOM = re.compile(r"(belirti|symptom|olduğunda|when\b|sonra\b|adım|reproduce|yeniden üret|stack ?trace|at [\w.$]+\()", re.I)
ROOT = re.compile(r"(kök neden|root cause|susturma|bastırma|don't suppress|do not suppress)", re.I)


def classify(text):
    files = len(set(re.findall(r"\b[\w/-]+\.(?:java|kt|py|ts|js|json|gradle)\b", text)))
    risky = re.search(r"(mimari|architecture|refactor|tasarım|design|güvenlik|security|migration|canlı sunucu|production|veri kaybı|data loss)", text, re.I)
    trivial = re.search(r"(typo|yazım hatası|rename|yeniden adlandır|log satırı|değişken adı)", text, re.I)
    if trivial and files <= 1:
        return "XS", "profil yok; plan modu gereksiz (H62)"
    if risky:
        return "L", "Maksimum profil (G1–G7, gerekirse G8); plan modu (H16)"
    if files >= 2 or len(text) > 600:
        return "M", "Dengeli profil (G1+G2+G6+G7)"
    return "S", "Hızlı profil (G2+G7)"


def lint(text):
    res = []
    for name, rx, hint, lever in CHECKS:
        res.append({"check": name, "ok": bool(re.search(rx, text, re.I)), "hint": hint, "lever": lever})
    if BUG.search(text):
        res.append({"check": "belirti tarifi", "ok": bool(SYMPTOM.search(text)), "hint": "belirti, olası yer ve 'düzeldi' tanımı + tam stack trace", "lever": "H61/H60"})
        res.append({"check": "kök neden talebi", "ok": bool(ROOT.search(text)), "hint": "\"kök nedeni düzelt, hatayı susturma, build'in geçtiğini doğrula\"", "lever": "H60"})
    cls, prof = classify(text)
    return {"checks": res, "class": cls, "profile": prof, "length": len(text)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt", nargs="?", help="prompt text, or '-' for stdin")
    p.add_argument("--file"); p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    if a.file:
        text = open(a.file, encoding="utf-8").read()
    elif a.prompt == "-" or (a.prompt is None and not sys.stdin.isatty()):
        text = sys.stdin.read()
    elif a.prompt:
        text = a.prompt
    else:
        p.print_help(); return 2
    r = lint(text)
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return 0
    miss = [c for c in r["checks"] if not c["ok"]]
    print(f"Görev sınıfı (öneri, değiştirebilirsin): {r['class']} → {r['profile']}")
    for c in r["checks"]:
        print(f"  {'✓' if c['ok'] else '✗'} {c['check']}" + ("" if c["ok"] else f" — {c['hint']} ({c['lever']})"))
    print(f"\n{len(miss)} eksik madde. Keşif/belirsiz istemler bilinçli olarak serbest bırakılabilir [D: best-practices].")
    return 0


if __name__ == "__main__":
    sys.exit(main())
