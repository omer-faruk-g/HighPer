#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — duplicate / overlapping skill, agent, command and hook detection (READ-ONLY). F1, F2, H66.

Compares NAMES and DESCRIPTIONS only (never file bodies):
  - same name loaded from two places (e.g. ~/.claude/skills and a plugin) → loaded twice [D: F2]
  - the same hook command registered twice (settings + plugin) → runs twice [D: F2]
  - descriptions that overlap strongly (word Jaccard ≥ threshold) → wrong skill may trigger [D: H66]
The user decides which one stays; nothing is changed.

  --home DIR   --cwd DIR   --threshold 0.45   --json   --dry-run (no-op)
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_perf import claude_home, frontmatter, hooks_list, installed_plugins, load_sources  # noqa: E402

STOP = set("the a an and or to of for in on with when use this that is are be by from as it your you user asks ve ile için bir bu da de ya".split())


def words(text):
    return {w for w in re.findall(r"[a-zçğıöşü0-9]{3,}", text.lower()) if w not in STOP}


def collect(home, cwd):
    items = []  # (kind, name, origin, description)
    roots = [("user", home), ("project", cwd / ".claude")]
    roots += [(f"plugin:{p['name']}", Path(p["path"])) for p in installed_plugins(home) if p["enabled"]]
    for origin, root in roots:
        for p in (root / "skills").glob("*/SKILL.md") if (root / "skills").is_dir() else []:
            fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            items.append(("skill", fm.get("name") or p.parent.name, origin, fm.get("description", "")))
        for kind in ("agents", "commands"):
            for p in (root / kind).glob("*.md") if (root / kind).is_dir() else []:
                fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
                items.append((kind[:-1], fm.get("name") or p.stem, origin, fm.get("description", "")))
    return items


def detect(home, cwd, threshold):
    items = collect(home, cwd)
    by_name = defaultdict(list)
    for kind, name, origin, _ in items:
        by_name[(kind, name)].append(origin)
    dup_names = [{"kind": k, "name": n, "origins": o} for (k, n), o in by_name.items() if len(o) > 1]
    hooks = hooks_list(load_sources(home, cwd), home)
    cmd = defaultdict(list)
    for h in hooks:
        cmd[(h["event"], h["command_full"])].append(h["origin"] + (f" ({h['matcher']})" if h["matcher"] else ""))
    dup_hooks = [{"event": e, "command": c[:70], "origins": o} for (e, c), o in cmd.items() if len(o) > 1]
    overlap = []
    desc = [(k, n, o, words(d)) for k, n, o, d in items if d]
    for (k1, n1, o1, w1), (k2, n2, o2, w2) in combinations(desc, 2):
        if n1 == n2 or not w1 or not w2:
            continue
        j = len(w1 & w2) / len(w1 | w2)
        if j >= threshold:
            overlap.append({"a": f"{k1}:{n1} [{o1}]", "b": f"{k2}:{n2} [{o2}]", "jaccard": round(j, 2)})
    overlap.sort(key=lambda x: -x["jaccard"])
    return {"items": len(items), "duplicate_names": dup_names, "duplicate_hooks": dup_hooks, "overlapping_descriptions": overlap[:15]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home"); p.add_argument("--cwd"); p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = detect(claude_home(a.home), Path(a.cwd or os.getcwd()), a.threshold)
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return 0
    print(f"=== {r['items']} skill/ajan/komut tarandı (yalnız ad + açıklama) ===")
    print(f"Çift yüklenen ad ({len(r['duplicate_names'])}):")
    for d in r["duplicate_names"]:
        print(f"  {d['kind']} '{d['name']}': {', '.join(d['origins'])}")
    print(f"Çift kayıtlı hook ({len(r['duplicate_hooks'])}):")
    for d in r["duplicate_hooks"]:
        print(f"  {d['event']} :: {d['command']} ← {', '.join(d['origins'])}")
    print(f"Örtüşen açıklamalar (Jaccard ≥ {a.threshold}) ({len(r['overlapping_descriptions'])}):")
    for d in r["overlapping_descriptions"]:
        print(f"  {d['jaccard']}  {d['a']}  ↔  {d['b']}")
    print("\nHangisinin kalacağına sen karar verirsin; HighPer hiçbir şeyi kaldırmaz (İlke 1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
