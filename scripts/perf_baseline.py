#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — performance baseline from local transcripts (READ-ONLY, counters/durations only).

Reads ~/.claude/projects/*/*.jsonl LOCALLY. Never prints or stores raw message text:
only counts, ratios and durations. Before parsing, the line schema is checked; if the
format is not recognised the script stops and says so (spec E1).

Per session and in total:
  P3 tur verimi   : user turns, API requests (deduped by message id), tool calls,
                    repeated identical Bash commands, repeated Read of the same file (F3)
  P5 güvenilirlik : failed tool calls (is_error) by class — izin/hook, bulunamadı,
                    zaman aşımı, sandbox, Edit eşleşmedi, diğer (F4); API errors; interruptions
  P2 gecikme      : turn duration median/p90 (prompt → last activity), idle gaps >1h (H30/K1-2)
  P4 bağlam       : compactions, peak context, cache read share of input-side tokens (H28)
  H65 tetikleyici : identical user prompts repeated (hash only, no text)

  --since YYYY-MM-DD   --last N   --projects DIR   --json   --dry-run (no-op)
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ERR_CLASSES = [
    ("izin/hook", re.compile(r"permission|denied|not allowed|blocked by|hook|requires approval|user rejected|reddedildi", re.I)),
    ("Edit eşleşmedi", re.compile(r"string to replace not found|old_string|not unique|has not been read|modified since read", re.I)),
    ("bulunamadı", re.compile(r"no such file|not found|enoent|does not exist|cannot find|could not find", re.I)),
    ("zaman aşımı", re.compile(r"timed? ?out|timeout", re.I)),
    ("sandbox", re.compile(r"sandbox|operation not permitted", re.I)),
]


def lp(p):
    s = os.path.abspath(str(p))
    return "\\\\?\\" + s if os.name == "nt" and not s.startswith("\\\\?\\") else s


def mtime(p):
    try:
        return os.stat(lp(p)).st_mtime
    except OSError:
        return 0


def ts(o):
    t = o.get("timestamp")
    if not t:
        return None
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def schema_ok(path):
    """Spec E1: check a sample of lines has the fields we rely on."""
    try:
        with open(lp(path), encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh):
                if i > 400:
                    break
                try:
                    o = json.loads(raw)
                except ValueError:
                    continue
                if o.get("type") in ("user", "assistant") and "message" in o and "timestamp" in o:
                    return True
    except OSError:
        return None
    return False


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    return ""


def analyze(path):
    s = Counter()
    tools, errs = Counter(), Counter()
    bash_cmds, reads, prompts = Counter(), Counter(), Counter()
    seen_ids, ctx = set(), []
    cache_read = input_side = 0
    turn_starts, last_activity, durations, idle = None, None, [], 0
    uses = {}
    with open(lp(path), encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                o = json.loads(raw)
            except ValueError:
                continue
            t = o.get("type")
            stamp = ts(o)
            if o.get("isCompactSummary") or o.get("compactMetadata"):
                s["compactions"] += 1
            if o.get("isApiErrorMessage"):
                s["_api_msg"] += 1
            if t == "system" and o.get("subtype") == "api_error":
                s["_api_sys"] += 1
            msg = o.get("message") or {}
            if t == "assistant":
                mid = msg.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    u = msg.get("usage") or {}
                    tot = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                    ctx.append(tot)
                    input_side += tot
                    cache_read += u.get("cache_read_input_tokens") or 0
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        name = c.get("name") or "?"
                        tools[name] += 1
                        inp = c.get("input") or {}
                        uses[c.get("id")] = name
                        if name in ("Bash", "PowerShell") and inp.get("command"):
                            bash_cmds[hashlib.sha1(inp["command"].strip().encode()).hexdigest()] += 1
                        if name == "Read" and inp.get("file_path"):
                            reads[(inp["file_path"], inp.get("offset"), inp.get("limit"))] += 1
                if stamp:
                    last_activity = stamp
            elif t == "user":
                content = msg.get("content")
                items = content if isinstance(content, list) else None
                if items and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in items):
                    for c in items:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                            s["tool_errors"] += 1
                            etext = text_of(c.get("content"))  # classified locally, never output
                            cls = next((n for n, rx in ERR_CLASSES if rx.search(etext)), "diğer")
                            errs[(uses.get(c.get("tool_use_id"), "?"), cls)] += 1
                    if stamp:
                        last_activity = stamp
                    continue
                txt = text_of(content)
                if "[Request interrupted" in txt:
                    s["interruptions"] += 1
                    continue
                if o.get("isMeta") or o.get("isCompactSummary") or not txt.strip() or txt.lstrip().startswith("<"):
                    continue
                s["user_turns"] += 1
                prompts[hashlib.sha1(re.sub(r"\s+", " ", txt.strip().lower()).encode()).hexdigest()] += 1
                if turn_starts and last_activity and last_activity >= turn_starts:
                    durations.append(last_activity - turn_starts)
                if last_activity and stamp and stamp - last_activity > 3600:
                    idle += 1
                turn_starts = stamp
            elif stamp and t in ("attachment",):
                last_activity = stamp
    if turn_starts and last_activity and last_activity >= turn_starts:
        durations.append(last_activity - turn_starts)
    s["api_errors"] = max(s.pop("_api_msg", 0), s.pop("_api_sys", 0))  # same error can carry both markers
    s["api_requests"] = len(seen_ids)
    s["tool_calls"] = sum(tools.values())
    s["repeat_bash"] = sum(n - 1 for n in bash_cmds.values() if n > 1)
    s["repeat_read"] = sum(n - 1 for n in reads.values() if n > 1)
    s["repeat_prompts"] = sum(n - 1 for n in prompts.values() if n > 1)
    s["idle_gaps_over_1h"] = idle
    return {
        "session": Path(path).stem[:8], "project": Path(path).parent.name[-32:], "counts": dict(s),
        "tool_error_rate": round(s["tool_errors"] / s["tool_calls"], 3) if s["tool_calls"] else 0.0,
        "error_classes": {f"{k[0]}:{k[1]}": v for k, v in errs.most_common()},
        "top_tools": dict(tools.most_common(6)),
        "turn_minutes": {"median": round(statistics.median(durations) / 60, 1) if durations else None,
                         "p90": round(sorted(durations)[int(0.9 * (len(durations) - 1))] / 60, 1) if durations else None,
                         "n": len(durations)},
        "context": {"peak": max(ctx) if ctx else 0, "median": int(statistics.median(ctx)) if ctx else 0},
        "cache_read_share": round(cache_read / input_side, 3) if input_side else None,
        "last_modified": datetime.datetime.fromtimestamp(mtime(path)).strftime("%Y-%m-%d"),
    }


def baseline(root=None, since=None, last=None):
    root = Path(root) if root else Path.home() / ".claude" / "projects"
    files = sorted(root.glob("*/*.jsonl"), key=mtime, reverse=True)
    if since:
        cut = datetime.datetime.strptime(since, "%Y-%m-%d").timestamp()
        files = [f for f in files if mtime(f) >= cut]
    seen, sessions, unknown = set(), [], []
    for f in files:
        if f.stem in seen:
            continue
        seen.add(f.stem)
        ok = schema_ok(f)
        if ok is False:
            unknown.append(f.stem[:8])
            continue
        if ok is None:
            continue
        r = analyze(f)
        if r["counts"].get("api_requests", 0) >= 2:  # skip empty/synthetic one-request sessions
            sessions.append(r)
        if last and len(sessions) >= last:
            break
    total = Counter()
    for r in sessions:
        total.update(r["counts"])
    return {"root": str(root), "sessions": sessions, "total": dict(total), "unrecognized_schema": unknown,
            "tool_error_rate": round(total["tool_errors"] / total["tool_calls"], 3) if total["tool_calls"] else 0.0}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--since"); p.add_argument("--last", type=int); p.add_argument("--projects")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    b = baseline(a.projects, a.since, a.last)
    if a.json:
        print(json.dumps(b, indent=1, ensure_ascii=False)); return 0
    if b["unrecognized_schema"] and not b["sessions"]:
        print("DUR: kayıt biçimi tanınmadı (beklenen: type=user/assistant + message + timestamp). Sürüm değişmiş olabilir; ham veri okunmadı.")
        return 1
    if not b["sessions"]:
        print(f"Kayıt bulunamadı: {b['root']}"); return 0
    t = b["total"]
    print(f"=== Taban çizgisi: {len(b['sessions'])} oturum (yalnız sayaç/süre; ham metin yok) ===")
    print(f"  kullanıcı turu {t.get('user_turns', 0)} | API isteği {t.get('api_requests', 0)} | araç çağrısı {t.get('tool_calls', 0)}")
    print(f"  P5 başarısız araç {t.get('tool_errors', 0)} (oran {b['tool_error_rate']}) | API hatası {t.get('api_errors', 0)} | kesinti {t.get('interruptions', 0)}")
    print(f"  P3 tekrar Bash {t.get('repeat_bash', 0)} | tekrar Read {t.get('repeat_read', 0)} | aynı istem tekrarı {t.get('repeat_prompts', 0)}")
    print(f"  P4 sıkıştırma {t.get('compactions', 0)} | P2 1 saatten uzun boşta kalıp devam {t.get('idle_gaps_over_1h', 0)}")
    print("\n  oturum    proje                             tur  istek  araç  hata%  tekrarB  tekrarR  tur_dk(med/p90)  bağlam_peak  önbellek")
    for r in b["sessions"]:
        c = r["counts"]; tm = r["turn_minutes"]
        print(f"  {r['session']}  {r['project']:<32}  {c.get('user_turns', 0):>3}  {c.get('api_requests', 0):>5}  {c.get('tool_calls', 0):>4}  "
              f"{r['tool_error_rate'] * 100:>5.1f}  {c.get('repeat_bash', 0):>7}  {c.get('repeat_read', 0):>7}  "
              f"{str(tm['median']) + '/' + str(tm['p90']):>15}  {r['context']['peak']:>11,}  {r['cache_read_share']}")
    classes = Counter()
    for r in b["sessions"]:
        classes.update(r["error_classes"])
    if classes:
        print("\n  Başarısız araç kümeleri (araç:sınıf → sayı): " + ", ".join(f"{k} {v}" for k, v in classes.most_common(8)))
    print("\nGürültü uyarısı: tek oturum kanıt değildir; görev türü ve model farklı oturumlar karşılaştırılamaz (Bölüm E3).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
