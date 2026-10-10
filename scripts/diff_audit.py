#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — diff audit before delivery (O4). READ-ONLY: runs only `git status`/`git diff`.

Checks the working tree against HEAD (staged + unstaged + untracked):
  (a) changed files outside the allow-list / inside the deny-list (scope config of scope_guard.py)
  (b) changes not covered by --expect globs (scope leak vs. the acceptance criteria)
  (c) deleted / renamed files
  (d) generated or binary files (build/, out/, .gradle/, run/, *.jar, *.class, generated/)
  (e) weakened tests: removed assert/@Test lines, added @Disabled/@Ignore/skip, deleted test files
  (f) secrets/keys in added lines
Findings are split in two classes (DZ-J1): "doğruluk/gereksinim" and "isteğe bağlı"
(added TODO/FIXME, debug prints, very large single-file change). Output: numbers and file
names only — no diff text, no commentary.

  python diff_audit.py [--repo DIR] [--expect 'src/main/java/**' ...] [--base HEAD] [--json] [--dry-run]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scope_guard import glob_re, load_config  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GENERATED = re.compile(r"(^|/)(build|out|\.gradle|run|generated|bin|target|node_modules)/|\.(jar|class|zip|exe|dll|so|png|jpg|ogg)$", re.I)
TEST_FILE = re.compile(r"(^|/)(src/test/|tests?/)|(Test|Tests|IT)\.(java|kt)$|(^|/)test_.*\.py$|\.(spec|test)\.[jt]sx?$")
ASSERT = re.compile(r"\b(assert\w*|@Test|expect\(|verify\(|should\.)", re.I)
SKIP = re.compile(r"(@Disabled|@Ignore|assumeTrue\(\s*false|@pytest\.mark\.skip|\bxit\(|\bit\.skip\(|\.skip\(|@Tag\(\"slow\"\))")
SECRET = re.compile(r"(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(?<![A-Za-z])(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{6,})", re.I)
DEBUG = re.compile(r"(System\.out\.println|printStackTrace\(\)|console\.log\(|\bprint\(\s*['\"]DEBUG)")


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", errors="replace")


def audit(repo, base="HEAD", expect=None):
    code, _ = git(repo, "rev-parse", "--is-inside-work-tree")
    if code != 0:
        return {"error": f"{repo} bir git deposu değil"}
    _, status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    _, names = git(repo, "diff", "--name-status", "-M", base)
    _, numstat = git(repo, "diff", "--numstat", base)
    _, patch = git(repo, "diff", "-U0", base)
    files, deleted, renamed, binary, big = set(), [], [], [], []
    for line in names.splitlines():
        parts = line.split("\t")
        st = parts[0]
        if st.startswith("R") and len(parts) == 3:
            renamed.append(f"{parts[1]} → {parts[2]}"); files.add(parts[2])
        elif st == "D":
            deleted.append(parts[1]); files.add(parts[1])
        elif len(parts) >= 2:
            files.add(parts[-1])
    for line in status.splitlines():
        if line.startswith("??"):
            files.add(line[3:].strip().strip('"'))
    for line in numstat.splitlines():
        a, d, f = (line.split("\t") + ["", "", ""])[:3]
        if a == "-" and d == "-":
            binary.append(f)
        elif a.isdigit() and d.isdigit() and int(a) + int(d) > 400:
            big.append(f"{f} (+{a}/-{d})")
    cfg = load_config(repo)
    out_of_scope = []
    if cfg:
        for f in sorted(files):
            if any(glob_re(x).match(f) for x in cfg["deny"]) or (cfg["allow"] and not any(glob_re(x).match(f) for x in cfg["allow"])):
                out_of_scope.append(f)
    leak = sorted(f for f in files if expect and not any(glob_re(x).match(f) for x in expect))
    generated = sorted({f for f in files if GENERATED.search(f)} | set(binary))
    weakened, secrets, todos, debug = {}, [], [], []
    cur = None
    for line in patch.splitlines():
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
            continue
        if line.startswith("--- a/"):
            prev = line[6:]
            if cur is None:
                cur = prev
            continue
        if not cur or line.startswith(("@@", "diff ", "index ")):
            continue
        is_test = bool(TEST_FILE.search(cur))
        if line.startswith("-") and is_test and ASSERT.search(line):
            weakened[cur] = weakened.get(cur, 0) + 1
        if line.startswith("+"):
            if is_test and SKIP.search(line):
                weakened[cur] = weakened.get(cur, 0) + 1
            if SECRET.search(line):
                secrets.append(cur)
            if re.search(r"\b(TODO|FIXME|XXX)\b", line):
                todos.append(cur)
            if DEBUG.search(line):
                debug.append(cur)
    for f in deleted:
        if TEST_FILE.search(f):
            weakened[f] = weakened.get(f, 0) + 1
    # untracked new files are not in `git diff`: scan their lines as "added" (read-only)
    for line in status.splitlines():
        if not line.startswith("??"):
            continue
        f = line[3:].strip().strip('"')
        path = Path(repo) / f
        if GENERATED.search(f) or not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            binary.append(f)
            continue
        for l in body.splitlines():
            if SECRET.search(l):
                secrets.append(f)
            if re.search(r"\b(TODO|FIXME|XXX)\b", l):
                todos.append(f)
            if DEBUG.search(l):
                debug.append(f)
            if TEST_FILE.search(f) and SKIP.search(l):
                weakened[f] = weakened.get(f, 0) + 1
    generated = sorted(set(generated) | set(binary))
    correctness = {"(a) kapsam dışı/yasak": out_of_scope, "(b) kabul ölçütü dışında değişiklik": leak,
                   "(c) silinen": deleted, "(c) yeniden adlandırılan": renamed, "(d) üretilmiş/ikili": generated,
                   "(e) zayıflatılmış test": [f"{k} ({v})" for k, v in weakened.items()], "(f) gizli bilgi şüphesi": sorted(set(secrets))}
    optional = {"eklenen TODO/FIXME": sorted(set(todos)), "eklenen debug çıktısı": sorted(set(debug)), "çok büyük dosya değişikliği (>400 satır)": big}
    return {"repo": repo, "changed_files": len(files), "scope_config": cfg["source"] if cfg else None,
            "correctness": correctness, "optional": optional}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default="."); p.add_argument("--base", default="HEAD"); p.add_argument("--expect", nargs="*")
    p.add_argument("--json", action="store_true"); p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    r = audit(os.path.abspath(a.repo), a.base, a.expect)
    if a.json or "error" in r:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return 0 if "error" not in r else 1
    n_corr = sum(len(v) for v in r["correctness"].values())
    print(f"=== diff denetimi: {r['changed_files']} değişen dosya; kapsam yapılandırması: {r['scope_config'] or 'yok'} ===")
    print(f"Doğruluk/gereksinim bulguları: {n_corr}")
    for k, v in r["correctness"].items():
        if v:
            print(f"  {k}: {len(v)} → {', '.join(v[:10])}")
    print("İsteğe bağlı:")
    for k, v in r["optional"].items():
        if v:
            print(f"  {k}: {len(v)} → {', '.join(v[:10])}")
    if not a.expect:
        print("  (b) için kabul ölçütü glob'ları verilmedi (--expect) — kapsam sızıntısı denetlenmedi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
