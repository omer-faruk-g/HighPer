#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — deterministic "done" gate, Stop hook (O2). Template; installed only with your approval.

Runs YOUR verification commands when Claude tries to finish. If one fails it returns
{"decision": "block", "reason": "..."} so Claude keeps working (Stop decision control,
code.claude.com/docs/en/hooks, verified 2026-10-10). If all pass it prints nothing (stop allowed).
Claude Code overrides a Stop hook after 8 consecutive continuations (CLAUDE_CODE_STOP_HOOK_BLOCK_CAP,
default 8, resets when Claude calls a tool) — then the turn ends with the gate NOT passed: the
delivery must be labelled "DOĞRULANMADI" (that cap is itself a blind spot, references/blind-spots.md).
It never touches permissions.

Config (JSON), first found wins: $HIGHPER_VERIFY, <project>/.claude/highper-verify.json
  {"commands": ["./gradlew compileJava -q", "./gradlew test --tests '*Handler*' -q"], "timeout_sec": 600}
  Optional "budget_sec" (default 840): total time for all commands. Keep it BELOW the hook's
  "timeout" in settings.json (900 in the SKILL.md snippet): if Claude Code kills the hook first,
  the stop goes through unverified. On timeout the whole process tree is killed and the stop is
  blocked (exit 124). A config file that cannot be read also blocks (fail-closed, O1).
No config → does nothing. Commands run with bash when available (Git Bash on Windows).
Keep them FAST (H18): a slow gate on every stop hurts latency (P2).

  --dry-run   show which commands would run, run nothing
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIT = re.compile(r"(error|exception|fail|caused by|what went wrong|expected|assert)", re.I)


def real_path(p):
    """MSIX apps (Claude desktop, Store Python) see AppData/Roaming through different virtual views;
    fall back to the package's LocalCache copy when the plain path is not visible."""
    p = Path(p)
    if p.exists():
        return p
    parts = p.parts
    low = [x.lower() for x in parts]
    for i in range(len(low) - 1):
        if low[i] == "appdata" and low[i + 1] == "roaming":
            tail = Path(*parts[i + 2:]) if len(parts) > i + 2 else Path()
            for cand in (Path(*parts[:i + 1]) / "Local" / "Packages").glob("*/LocalCache/Roaming"):
                if (cand / tail).exists():
                    return cand / tail
            break
    return p


def load_config(cwd):
    for c in (os.environ.get("HIGHPER_VERIFY"), str(real_path(Path(cwd) / ".claude" / "highper-verify.json"))):
        if c and Path(c).is_file():
            try:
                cfg = json.loads(Path(c).read_text(encoding="utf-8"))
                return {"commands": list(cfg.get("commands", [])), "timeout": int(cfg.get("timeout_sec", 600)),
                        "budget": int(cfg.get("budget_sec", 840)), "source": c}
            except (ValueError, TypeError, AttributeError) as e:  # fail-closed: a broken gate must not pass silently
                return {"commands": [], "timeout": 0, "source": c, "broken": f"{type(e).__name__}: {e}"}
    return None


def kill_tree(p):
    """Kill the command AND its children; otherwise a hung grandchild keeps the pipe open and the
    gate waits past its own timeout until Claude Code's hook timeout ends it (= stop allowed)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True, timeout=15)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        p.kill()
    except OSError:
        pass


def run(cmd, cwd, timeout):
    bash = shutil.which("bash")
    argv = [bash, "-lc", cmd] if bash else cmd
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    try:
        p = subprocess.Popen(argv, cwd=cwd, shell=not bash, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    except OSError as e:
        return 127, str(e)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        kill_tree(p)
        try:
            out, _ = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = b""
        return 124, f"zaman aşımı ({timeout} sn); süreç ağacı sonlandırıldı\n" + out.decode("utf-8", errors="replace")


def summary(out, n=25):
    lines = out.splitlines()
    hits = [l for l in lines if HIT.search(l)]
    pick = (hits[:n] if hits else lines[-n:])
    return "\n".join(pick)[:1500]


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__); return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = {}
    cwd = str(real_path(event.get("cwd") or os.getcwd()))
    cfg = load_config(cwd)
    if cfg and cfg.get("broken"):
        reason = (f"HighPer verify_gate: {cfg['source']} okunamadı ({cfg['broken']}). Kapı fail-closed: "
                  "yapılandırmayı düzelt veya kaldır; o zamana kadar teslim \"DOĞRULANMADI\".")
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0
    if not cfg or not cfg["commands"]:
        if "--dry-run" in sys.argv:
            print("yapılandırma yok → kapı devre dışı (Stop serbest)")
        return 0
    if "--dry-run" in sys.argv:
        print(f"{cfg['source']}: şu komutlar sırayla çalışırdı (zaman aşımı {cfg['timeout']} sn):")
        for c in cfg["commands"]:
            print(f"  {c}")
        print(f"stop_hook_active={event.get('stop_hook_active')}; başarısızlıkta decision=block; 8 ardışık engelden sonra Claude Code turu bitirir.")
        return 0
    deadline = time.monotonic() + cfg["budget"]
    for c in cfg["commands"]:
        left = int(deadline - time.monotonic())
        code, out = run(c, cwd, min(cfg["timeout"], left)) if left > 0 else (124, f"toplam bütçe ({cfg['budget']} sn) bitti; komut çalıştırılmadı")
        if code != 0:
            reason = (f"HighPer verify_gate: `{c}` çıkış kodu {code}. Kök nedeni düzelt (testi zayıflatma), sonra yeniden doğrula.\n"
                      f"{summary(out)}\n"
                      "Not: bu kapı art arda 8 kez engellerse tur biter; o durumda teslimi \"DOĞRULANMADI\" olarak işaretle.")
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
