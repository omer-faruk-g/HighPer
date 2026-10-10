#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — canary mini task (O10). Runs only with your approval (--yes).

A 1–3 minute known-answer task that catches one class of sudden degradation early
(wrong result, empty output, garbled characters, obvious syntax error — the symptom
class of the September 2025 incidents [D]). It does NOT guarantee anything.

  prompt                       print the canary task for Claude (paste it at task start)
  check --dir DIR [--yes]      run the known-answer tests against DIR/highper_canary.py
                               (executes that file in a subprocess with a timeout; without
                               --yes nothing is executed — dry run)
  check-text FILE              scan a saved English/Turkish reply for foreign-script characters
                               (Thai, CJK) and emptiness — counts only, no text is printed
  --store F                    (with check --yes) append {date, version, pass 0/1} to F
On failure: STOP, /clear, `claude --safe-mode`, version/model check (incident_check.py), /feedback.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROMPT = """[HighPer kanarya — 1–3 dk]
highper_canary.py adında bir dosya oluştur ve içine yalnız şu fonksiyonu yaz (standart kütüphane):
  def rle(s: str) -> str
Run-length encoding: ardışık aynı karakterleri "<sayı><karakter>" biçiminde kodla.
Örnekler: rle("aaabcc") == "3a1b2c", rle("") == "", rle("z") == "1z".
Başka hiçbir dosyaya dokunma. Sonra şunu çalıştır ve çıktısını göster:
  python <HighPer>/scripts/canary.py check --dir . --yes"""

CASES = [("aaabcc", "3a1b2c"), ("", ""), ("z", "1z"), ("aaaaaaaaaaaa", "12a"), ("abAB", "1a1b1A1B"), ("ççğğğ", "2ç3ğ")]
HARNESS = """import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("c", sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cases = json.loads(sys.argv[2]); ok = 0
for i, o in cases:
    try:
        ok += (m.rle(i) == o)
    except Exception:
        pass
print(ok)
"""
FOREIGN = re.compile(r"[฀-๿一-鿿぀-ヿ가-힯]")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("prompt")
    ck = sub.add_parser("check"); ck.add_argument("--dir", default="."); ck.add_argument("--yes", action="store_true"); ck.add_argument("--store")
    ct = sub.add_parser("check-text"); ct.add_argument("file")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.cmd in (None, "prompt"):
        print(PROMPT); return 0
    if a.cmd == "check-text":
        text = Path(a.file).read_text(encoding="utf-8", errors="replace")
        n = len(FOREIGN.findall(text))
        print(f"boş yanıt: {'EVET' if not text.strip() else 'hayır'}; yabancı yazı sistemi karakteri: {n}")
        if n or not text.strip():
            print("KANARYA UYARISI: DUR → /clear, claude --safe-mode, incident_check.py, gerekirse /feedback (O10).")
            return 1
        return 0
    target = Path(a.dir) / "highper_canary.py"
    if not a.yes or a.dry_run:
        print(f"[dry-run] {target} bir alt süreçte {len(CASES)} bilinen-cevaplı testle çalıştırılırdı (zaman aşımı 20 sn). Onay için --yes.")
        return 0
    if not target.is_file():
        print(f"KANARYA BAŞARISIZ: {target} yok."); return 1
    try:
        r = subprocess.run([sys.executable, "-I", "-c", HARNESS, str(target), json.dumps(CASES)], capture_output=True, text=True, timeout=20)
        passed = int((r.stdout.strip() or "0").splitlines()[-1])
    except (subprocess.SubprocessError, ValueError):
        passed = 0
    ok = passed == len(CASES)
    print(f"Kanarya: {passed}/{len(CASES)} test geçti → {'GEÇTİ' if ok else 'BAŞARISIZ — DUR: /clear, claude --safe-mode, incident_check.py, /feedback (O10)'}")
    if a.store:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import pin_check
        try:
            data = json.loads(Path(a.store).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"runs": [], "escapes": []}
        data.setdefault("canary", []).append({"date": datetime.date.today().isoformat(), "claude_version": pin_check.current_state()["claude_version_latest"], "pass": int(ok)})
        Path(a.store).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
