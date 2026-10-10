#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — inefficiency hunt (`/highper hunt`, Section F). READ-ONLY.

Combines audit_perf + claude_md_lint + perf_baseline + dup_detect into at most 10
findings, each with: evidence (a measured number), axis (P1–P6), lever (H/F/G),
suggestion, trade-off and how to roll back. Priority: (1) correctness, (2) reliability,
(3) latency, (4) cost. A finding without data is marked "olası, doğrulanmadı" (İlke 7).
Where MinToken points the other way, both directions are shown (Section C).

  --since YYYY-MM-DD   --last N   --home DIR   --cwd DIR   --json   --dry-run (no-op)
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_perf  # noqa: E402
import claude_md_lint  # noqa: E402
import dup_detect  # noqa: E402
import perf_baseline  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRIO = {"doğruluk": 1, "güvenilirlik": 2, "gecikme": 3, "maliyet": 4}


def F(prio, axis, lever, finding, evidence, suggest, tradeoff, rollback, weight=0, mintoken=None):
    return {"priority": prio, "axis": axis, "lever": lever, "finding": finding, "evidence": evidence,
            "suggest": suggest, "tradeoff": tradeoff, "rollback": rollback, "weight": weight, "mintoken": mintoken}


def hunt(home, cwd, since=None, last=None):
    out = []
    b = perf_baseline.baseline(None if not home or home == audit_perf.claude_home() else home / "projects", since, last)
    t = b["total"]
    sessions = b["sessions"]
    if sessions:
        classes = {}
        for s in sessions:
            for k, v in s["error_classes"].items():
                classes[k] = classes.get(k, 0) + v
        edit = sum(v for k, v in classes.items() if k.endswith("Edit eşleşmedi"))
        perm = sum(v for k, v in classes.items() if k.endswith("izin/hook"))
        if edit >= 5:
            out.append(F("güvenilirlik", "P5/P3", "F4/H11", "Edit eşleşmeme döngüleri", f"{edit} başarısız Edit (old_string bulunamadı/dosya okunmadı)",
                         "düzenlemeden önce ilgili aralığı oku; 2 başarısız denemeden sonra dur, yöntemi değiştir veya /rewind", "ek bir Read turu", "-", edit))
        if perm >= 5:
            out.append(F("güvenilirlik", "P5/P3", "F4/H40", "izin/hook reddi kaynaklı boşa turlar", f"{perm} reddedilen araç çağrısı",
                         "sık reddedilen MEŞRU komut için dar allow kuralı (izin gevşetmeden, diff + onay)", "her yeni kural bir güven kararıdır", "kuralı settings'ten sil", perm))
        rate = b["tool_error_rate"]
        if rate >= 0.05:
            out.append(F("güvenilirlik", "P5", "F4", "yüksek araç hata oranı", f"oran {rate:.1%} ({t.get('tool_errors', 0)}/{t.get('tool_calls', 0)})",
                         "en sık sınıfı ele al: " + ", ".join(f"{k} {v}" for k, v in sorted(classes.items(), key=lambda x: -x[1])[:3]), "-", "-", int(rate * 1000)))
        long_s = [s for s in sessions if s["counts"].get("api_requests", 0) > 500 or s["context"]["peak"] > 600_000]
        if long_s:
            out.append(F("doğruluk", "P4/P1", "H8/G9 (DZ-J2: [D])", "çok uzun oturumlar (bağlam çürümesi riski)",
                         f"{len(long_s)} oturum >500 istek veya >600K bağlam (en büyük {max(s['context']['peak'] for s in long_s):,})",
                         "görev başına /clear; aynı görevde /compact <odak>; keşfi alt-ajana ver", "yeniden bağlam kurma", "-",
                         len(long_s) * 100, mintoken="aynı yön (MinToken B4/C62)"))
        idle = t.get("idle_gaps_over_1h", 0)
        if idle >= 3:
            out.append(F("doğruluk", "P4/P2", "H30/O11/K1-2", "1 saatten uzun boşluktan sonra aynı oturuma dönüş", f"{idle} kez",
                         "yeni görevse /clear veya yeni oturum; sürdürülecekse 'özetten sürdür'", "özet ayrıntı kaybedebilir", "-", idle * 10))
        rep = t.get("repeat_bash", 0) + t.get("repeat_read", 0)
        if rep >= 20:
            out.append(F("gecikme", "P3", "F3", "aynı komut/dosyanın tekrar çalıştırılması/okunması",
                         f"{t.get('repeat_bash', 0)} tekrar komut, {t.get('repeat_read', 0)} tekrar okuma",
                         "neden: sıkıştırma kaybı, belirsiz görev, eksik başarı ölçütü → H50 Compact Instructions, H15 ölçüt", "-", "-", rep))
        p90s = [s["turn_minutes"]["p90"] for s in sessions if s["turn_minutes"]["p90"]]
        if p90s and max(p90s) >= 30:
            out.append(F("gecikme", "P2", "F5/H26", "çok uzun turlar", f"tur süresi p90 en yüksek {max(p90s)} dk",
                         "uzun Gradle/sunucu işini arka plana al + Monitor; hızlı doğrulama (compileJava) önce", "arka plan çıktısını izleme gerekir", "-", int(max(p90s))))
        errs = t.get("api_errors", 0) + t.get("interruptions", 0)
        if errs >= 10:
            out.append(F("güvenilirlik", "P5", "H35/H36", "API hatası/kesinti", f"{t.get('api_errors', 0)} API hatası, {t.get('interruptions', 0)} kesinti",
                         "ağ/taban URL/zaman aşımı kontrolü (incident_check.py); tekrar ediyorsa /feedback", "-", "-", errs))
        if t.get("repeat_prompts", 0) >= 10:
            out.append(F("maliyet", "P3", "H65/G10", "aynı istemin tekrar tekrar yazılması", f"{t['repeat_prompts']} tekrar (yalnız hash sayımı)",
                         "tekrarlanan istemi skill'e, tekrarlanan düzeltmeyi CLAUDE.md'ye taşı (onayla)", "-", "-", t["repeat_prompts"]))
    else:
        out.append(F("doğruluk", "-", "E1", "oturum kaydı yok/okunamadı", "veri yok", "ölçüm olmadan öneri 'olası, doğrulanmadı' (İlke 7)", "-", "-"))
    a = audit_perf.audit(home, cwd, dict(os.environ))
    for r in a["risks"]:
        prio = "doğruluk" if r["lever"].startswith(("H45", "H44", "H3")) else ("güvenilirlik" if r["lever"] in ("H37", "H39") else "gecikme")
        out.append(F(prio, "-", r["lever"], r["risk"], f"{r['key']} = {r['value']} [{r['source']}]", r["suggest"], r["tradeoff"],
                     f"{r['key']} eski değerine dön", 50))
    for res in [claude_md_lint.lint_file(f, user_level=(f.resolve() == (home / 'CLAUDE.md').resolve()))
                for f in claude_md_lint.candidate_files(home, cwd)]:
        for sev, kind, msg, where in res["findings"]:
            if sev == 1:
                out.append(F("doğruluk", "P1", "F6/H12", f"CLAUDE.md: {kind}", f"{Path(res['file']).name}" + (f" satır {where}" if where else ""), msg, "-", "dosyanın önceki hali (git)", 40))
    if not any(f.endswith("CLAUDE.md") and Path(f).parent != home for f in map(str, claude_md_lint.candidate_files(home, cwd))):
        out.append(F("doğruluk", "P1", "H12/H15/D2", "proje CLAUDE.md yok", f"{cwd}", "kısa CLAUDE.md + doğrulama merdiveni + Compact Instructions (taslak: gradle_perf.py)", "birkaç yüz token sabit yük", "dosyayı sil", 30,
                     mintoken="MinToken: <200 satır tut (C8)"))
    d = dup_detect.detect(home, cwd, 0.45)
    if d["duplicate_names"] or d["duplicate_hooks"]:
        out.append(F("güvenilirlik", "P1/P2", "F2", "çift yüklenen skill/hook", f"{len(d['duplicate_names'])} ad, {len(d['duplicate_hooks'])} hook",
                     "hangisinin kalacağını sen seç", "-", "-", 20))
    if d["overlapping_descriptions"]:
        top = d["overlapping_descriptions"][0]
        out.append(F("doğruluk", "P1", "F2/H66", "örtüşen skill/ajan açıklamaları (yanlış tetiklenme)", f"{len(d['overlapping_descriptions'])} çift; en yüksek {top['jaccard']}: {top['a']} ↔ {top['b']}",
                     "açıklamaları ayrıştır veya birini /<ad> ile elle çağır", "-", "-", int(top["jaccard"] * 100)))
    out.sort(key=lambda f: (PRIO.get(f["priority"], 9), -f["weight"]))
    return out[:10], b


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--since"); p.add_argument("--last", type=int); p.add_argument("--home"); p.add_argument("--cwd")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    findings, b = hunt(audit_perf.claude_home(a.home), Path(a.cwd or os.getcwd()), a.since, a.last)
    if a.json:
        print(json.dumps(findings, indent=1, ensure_ascii=False)); return 0
    print(f"=== HighPer verimsizlik avı — {len(findings)} bulgu (en çok 10; öncelik: doğruluk > güvenilirlik > gecikme > maliyet) ===")
    for i, f in enumerate(findings, 1):
        print(f"\n{i}. [{f['priority']}] {f['finding']}  ({f['lever']}, {f['axis']})")
        print(f"   kanıt: {f['evidence']}\n   öneri: {f['suggest']}\n   takas: {f['tradeoff']} | geri alma: {f['rollback']}")
        if f["mintoken"]:
            print(f"   MinToken: {f['mintoken']}")
    print(f"\nVeri: {len(b['sessions'])} oturum (yalnız sayaç). Hiçbir şey değiştirilmedi; uygulamak için diff + açık onay.")
    print("Gürültü: tek oturum kanıt değildir; önce/sonra ölçümü için references/axes-and-measurement.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
