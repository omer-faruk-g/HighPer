#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — Markdown report: eksen → ölçülen değer → şüpheli kaldıraç → öneri → takas → geri alma (E6).

Runs hunt.py in-process (read-only) and renders the report. This is the ONLY HighPer
script that writes a file, and only to the path you give with --out. Without --out, or
with --dry-run, the report is printed to stdout and nothing is written.
Every report carries the noise/sample warning and contains no raw message text.

  python report.py                         # print to stdout
  python report.py --out highper-rapor.md  # write to that file only
  --since YYYY-MM-DD   --last N   --home DIR   --cwd DIR   --dry-run
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_perf  # noqa: E402
import hunt  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def render(findings, base, cwd):
    t = base["total"]
    lines = [f"# HighPer raporu — {datetime.date.today().isoformat()}", "",
             f"Proje: `{cwd}` · Veri: {len(base['sessions'])} oturum (yalnız sayaç ve süreler; ham mesaj metni yok).", "",
             "## Ölçülen taban", "",
             "| Eksen | Ölçüm | Değer |", "|---|---|---|",
             f"| P3 tur verimi | kullanıcı turu / API isteği / araç çağrısı | {t.get('user_turns', 0)} / {t.get('api_requests', 0)} / {t.get('tool_calls', 0)} |",
             f"| P5 güvenilirlik | başarısız araç (oran) | {t.get('tool_errors', 0)} ({base['tool_error_rate']:.1%}) |",
             f"| P5 güvenilirlik | API hatası / kesinti | {t.get('api_errors', 0)} / {t.get('interruptions', 0)} |",
             f"| P3 tekrar | tekrar komut / tekrar okuma | {t.get('repeat_bash', 0)} / {t.get('repeat_read', 0)} |",
             f"| P4 bağlam | sıkıştırma / 1 saatten uzun boşluk sonrası devam | {t.get('compactions', 0)} / {t.get('idle_gaps_over_1h', 0)} |", "",
             "## Bulgular (öncelik: doğruluk > güvenilirlik > gecikme > maliyet)", "",
             "| # | Eksen | Ölçülen değer | Şüpheli kaldıraç | Önerilen değişiklik | Takas | Geri alma |", "|---|---|---|---|---|---|---|"]
    for i, f in enumerate(findings, 1):
        cell = lambda s: str(s).replace("|", "\\|")
        lines.append(f"| {i} | {f['axis']} ({f['priority']}) | {cell(f['evidence'])} | {f['lever']}: {cell(f['finding'])} | {cell(f['suggest'])} | {cell(f['tradeoff'])} | {cell(f['rollback'])} |")
    mt = [f for f in findings if f.get("mintoken")]
    if mt:
        lines += ["", "## MinToken ile yan yana (Bölüm C; seçim senin)", ""]
        lines += [f"- {f['lever']}: HighPer → {f['suggest']} · MinToken → {f['mintoken']}" for f in mt]
    lines += ["", "## Gürültü ve örneklem uyarısı",
              "Tek oturum kanıt değildir. Önce/sonra karşılaştırması aynı görev türünde, aynı model/effort ile, en az 3 tekrar ister; "
              "birden çok şeyi aynı anda değiştirme (bisect). Bu rapor hiçbir yüzde/hız vaadi içermez; hiçbir ayar değiştirilmedi.", ""]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out"); p.add_argument("--since"); p.add_argument("--last", type=int)
    p.add_argument("--home"); p.add_argument("--cwd"); p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    cwd = Path(a.cwd or os.getcwd())
    findings, base = hunt.hunt(audit_perf.claude_home(a.home), cwd, a.since, a.last)
    md = render(findings, base, cwd)
    if a.out and not a.dry_run:
        Path(a.out).write_text(md, encoding="utf-8")
        print(f"Rapor yazıldı: {a.out}")
    else:
        print(md)
        if a.out:
            print(f"[dry-run] {a.out} yazılmadı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
