#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — scope guard, PreToolUse hook (O3). Adds a restriction; never loosens permissions.

Blocks writes outside the allow-list or inside the deny-list by exiting with code 2
(PreToolUse exit 2 "Blocks the tool call", stderr goes to Claude — code.claude.com/docs/en/hooks,
verified 2026-10-10). It never returns "allow" and never prints JSON, so the normal permission
flow and your allow/deny rules stay exactly as they are.

Config (JSON), first found wins: $HIGHPER_SCOPE, <project>/.claude/highper-scope.json
  {"allow": ["src/main/java/**", "src/main/resources/**"],
   "deny":  ["build/**", "run/**", ".gradle/**", "**/*.jar", "gradle/wrapper/**"]}
No config → the hook does nothing.

Checked tools: Edit, Write, MultiEdit, NotebookEdit (file path); Bash/PowerShell write targets
found heuristically: > >> tee cp mv rm touch mkdir sed -i, Set-Content Out-File Add-Content
Remove-Item Copy-Item Move-Item New-Item.
BLIND SPOTS (listed for the user, references/blind-spots.md): writes from compiled programs,
scripts, gradle tasks, interpreters (python -c), variables/globs in paths, network/remote
actions, and any write path the heuristics do not recognise. git is the real safety net (O5).

  --dry-run   read the hook JSON from stdin and print the decision instead of blocking
  --check PATH [--cwd DIR]   test a single path against the config
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FILE_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
PS_WRITE = re.compile(r"\b(Set-Content|Add-Content|Out-File|Remove-Item|Copy-Item|Move-Item|New-Item)\b[^|;]*?(?:-(?:Path|FilePath|Destination|LiteralPath)\s+)?['\"]?([^\s'\";|]+)", re.I)


def glob_re(pattern):
    i, out = 0, ""
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return re.compile("^" + out + "$")


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
    for c in (os.environ.get("HIGHPER_SCOPE"), str(real_path(Path(cwd) / ".claude" / "highper-scope.json"))):
        if c and Path(c).is_file():
            try:
                cfg = json.loads(Path(c).read_text(encoding="utf-8"))
                return {"allow": cfg.get("allow", []), "deny": cfg.get("deny", []), "source": c}
            except ValueError:
                return {"allow": [], "deny": ["**"], "source": c + " (BOZUK JSON: hepsi engellenir — fail-closed)"}
    return None


def rel(path, cwd):
    p = Path(path) if os.path.isabs(path) else Path(cwd) / path
    try:
        return PurePosixPath(os.path.relpath(os.path.normpath(str(p)), os.path.normpath(str(cwd))).replace("\\", "/"))
    except ValueError:  # other drive
        return PurePosixPath("../" + str(p).replace("\\", "/"))


def verdict(path, cwd, cfg):
    r = str(rel(path, cwd))
    if r.startswith("../"):
        return False, f"{path}: proje dizini dışında"
    if any(glob_re(d).match(r) for d in cfg["deny"]):
        return False, f"{r}: YASAK listesinde"
    if cfg["allow"] and not any(glob_re(a).match(r) for a in cfg["allow"]):
        return False, f"{r}: izin listesi dışında"
    return True, r


def bash_targets(cmd):
    t = []
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)  # quote-aware; ; && || | > become own tokens
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:  # unbalanced quotes: fall back to a raw scan (may over-match → fail-closed)
        t += re.findall(r"(?<![0-9&])>{1,2}\s*([^\s;&|<>]+)", cmd)
        toks = cmd.split()
    for i, tok in enumerate(toks[:-1]):
        if tok in (">", ">>", ">|", "&>", "&>>") and not (i and toks[i - 1].isdigit() and toks[i + 1].startswith("&")):
            if not toks[i + 1].startswith("&"):
                t.append(toks[i + 1])
    seps = {"&&", "||", ";", "|", "&", ";;", "(", ")", ">", ">>", "<", "|&", ">&", "&>"}
    for i, tok in enumerate(toks):
        if i and toks[i - 1] not in seps and toks[i - 1] not in ("sudo", "xargs", "command"):
            continue  # only the first word of a command segment is a program name
        base = os.path.basename(tok)
        seg = []
        for x in toks[i + 1:]:
            if x in seps:
                break
            seg.append(x)
        args = [x for x in seg if not x.startswith("-")]
        if base == "tee" and args:
            t += args
        elif base in ("cp", "mv") and len(args) >= 2:
            t.append(args[-1])
        elif base in ("rm", "touch", "mkdir", "rmdir") and args:
            t += args
        elif base == "sed" and "-i" in toks[i + 1:i + 4] and args:
            t.append(args[-1])
    t += [m.group(2) for m in PS_WRITE.finditer(cmd)]
    return [x for x in t if x and not x.startswith(("$", "/dev/null")) and x != "/dev/null" and x.lower() != "nul"]


def decide(event, cwd=None):
    cwd = cwd or event.get("cwd") or os.getcwd()
    cfg = load_config(cwd)
    if not cfg:
        return None, "yapılandırma yok"
    tool = event.get("tool_name", "")
    inp = event.get("tool_input") or {}
    if tool in FILE_TOOLS:
        targets = [inp.get(FILE_TOOLS[tool], "")]
    elif tool in ("Bash", "PowerShell"):
        targets = bash_targets(inp.get("command", ""))
    else:
        return None, "denetlenmeyen araç"
    for t in targets:
        ok, msg = verdict(t, cwd, cfg)
        if not ok:
            return False, f"HighPer scope_guard ({cfg['source']}): {msg}. İzinli: {cfg['allow'] or '(hepsi)'}; yasak: {cfg['deny']}. Kapsamı değiştirmek kullanıcının kararıdır."
    return True, f"{len(targets)} hedef kapsam içinde"


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__); return 0
    if "--check" in sys.argv:
        path = sys.argv[sys.argv.index("--check") + 1]
        cwd = sys.argv[sys.argv.index("--cwd") + 1] if "--cwd" in sys.argv else os.getcwd()
        cfg = load_config(cwd)
        print("yapılandırma yok" if not cfg else verdict(path, cwd, cfg)); return 0
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0  # never break the tool call on unreadable input
    try:
        ok, msg = decide(event)
    except Exception as e:  # fail-closed (O1): a guard bug must not let a write through silently
        ok, msg = False, f"HighPer scope_guard iç hata ({type(e).__name__}: {e}); güvenli tarafta kalıp engellendi."
    if "--dry-run" in sys.argv:
        print({None: "DOKUNMA", True: "İZİN (normal izin akışı sürer)", False: "ENGELLE (exit 2)"}[ok] + f" — {msg}")
        return 0
    if ok is False:
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
