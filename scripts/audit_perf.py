#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer — settings/env/plugin/hook/mod/MCP performance audit (READ-ONLY).

Reports VAR/YOK + value for every key on the spec's audit_perf checklist, flags
performance risks with the matching lever (H-number), lists installed tools
(MinToken, Headroom, Graphify, Ponytail, claude-mem, ECC, SkillSpector), plugins,
hooks, custom agents' models, MCP servers, and whether managed settings exist
(report only — HighPer never touches them).

Key names were checked against code.claude.com/docs on 2026-10-10 (VERIFIED below);
a key not found there is shown as "kurulu sürümde tanınmıyor olabilir".

  --home DIR        fake ~/.claude (testing)          --cwd DIR   project dir
  --no-process-env  ignore the current environment    --json      machine-readable
  --dry-run         no-op: this script never writes
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECKLIST = [
    "effortLevel", "maxEffortLevel", "modelSettings", "fallbackModel", "advisorModel", "fastMode",
    "fastModePerSessionOptIn", "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS", "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", "ultracode",
    "workflowKeywordTriggerEnabled", "workflowSizeGuideline", "CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "autoContinueAtUsageLimit", "CLAUDE_CODE_GOAL_CHECKIN_MINUTES",
    "ENABLE_TOOL_SEARCH", "MCP_TOOL_TIMEOUT", "MCP_TIMEOUT", "CLAUDE_CODE_MCP_STARTUP_WAIT_MS",
    "MAX_MCP_OUTPUT_TOKENS", "API_TIMEOUT_MS", "CLAUDE_ENABLE_STREAM_WATCHDOG", "CLAUDE_STREAM_IDLE_TIMEOUT_MS",
    "promptCacheTtl", "subagentPromptCacheTtl", "DISABLE_PROMPT_CACHING*", "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    "autoCompactWindow", "bashOutputMaxChars", "outputStyle", "permissions.defaultMode", "permissions.disableAutoMode",
    "autoMode.classifyAllShell", "sandbox.allowUnsandboxedCommands", "syncClaudeAiPlugins", "syncClaudeAiSkills",
    "skipWebFetchPreflight", "ENABLE_CLAUDEAI_MCP_SERVERS", "strictMcpConfig", "CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT",
    "CLAUDE_CODE_DISABLE_*", "CLAUDE_CODE_ENABLE_TODO_TOOLS", "worktree.sparsePaths", "disableAllHooks",
]

# (key, H-lever, condition(value)->bool, risk text, suggestion, trade-off)  — performance risks only
RISKS = [
    ("CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT", "H45", lambda v: str(v).lower() in ("1", "true"), "kısa sistem istemi + kısaltılmış araç açıklamaları: davranış/kalite riski", "kapat (yalnız bilinçli tercih ise bırak)", "token artar"),
    ("CLAUDE_CODE_DISABLE_CLAUDE_MDS", "H45", lambda v: str(v).lower() in ("1", "true"), "CLAUDE.md yüklenmiyor: proje kuralları yok", "kapat", "token artar"),
    ("CLAUDE_CODE_DISABLE_BUNDLED_SKILLS", "H45", lambda v: str(v).lower() in ("1", "true"), "yerleşik skill'ler (ör. /code-review, /verify) yok", "kapat", "token artar"),
    ("CLAUDE_CODE_DISABLE_ATTACHMENTS", "H45", lambda v: str(v).lower() in ("1", "true"), "@ dosya bahisleri düz metin: bağlam eksik kalabilir", "kapat", "token artar"),
    ("CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS", "H45/H49", lambda v: str(v).lower() in ("1", "true"), "commit/PR talimatı ve git durumu yok", "commit için Claude kullanıyorsan kapat", "token artar"),
    ("DISABLE_PROMPT_CACHING", "H28", lambda v: str(v).lower() in ("1", "true"), "önbellek kapalı: her tur yavaş ve pahalı", "kaldır", "yok"),
    ("autoContinueAtUsageLimit", "H39", lambda v: v is True, "limit sıfırlanınca iş GÖZETİMSİZ sürer", "gözetimsiz iş için --max-turns, zaman aşımı, bütçe ve bitiş koşulu ver; istemiyorsan false", "iş seni bekler"),
    ("autoMode.classifyAllShell", "H40", lambda v: v is True, "her kabuk komutu sınıflandırıcıdan geçer: gecikme", "dar allow kuralları + false (güvenlik kararı senin)", "daha az inceleme"),
    ("CLAUDE_CODE_SUBAGENT_MODEL", "H3", lambda v: "haiku" in str(v).lower(), "tüm alt-ajanlar küçük modele zorlanmış olabilir: P1 düşebilir", "alt-ajan bazında model: frontmatter kullan", "maliyet artar"),
    ("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "H25", lambda v: str(v).lower() in ("1", "true"), "teammate'li oturum plan modunda ≈7× token", "yalnız gerçekten paralel işte", "hız ↔ token"),
    ("ultracode", "H24", lambda v: bool(v), "önemli her görev workflow'a dönebilir", "bilinçli kullan", "hız ↔ çok yüksek token"),
    ("CLAUDE_STREAM_IDLE_TIMEOUT_MS", "H36", lambda v: str(v).isdigit() and int(v) < 120000, "kısa akış zaman aşımı: yavaş ağda yanlış kesilme", "artırmayı düşün", "gerçek takılmayı geç fark etme"),
]

AT_DEFAULT = [  # (H, text) — shown only when the user has not overridden it
    ("H1/DZ-J3", "effort: model varsayılanı (Opus/Sonnet/Haiku 5.5 → medium, Opus 4.7 → xhigh, diğerleri high)", ("effortLevel", "CLAUDE_CODE_EFFORT_LEVEL", "modelSettings")),
    ("H10", "otomatik sıkıştırma ≈967K (1M pencereli modeller)", ("autoCompactWindow", "CLAUDE_CODE_AUTO_COMPACT_WINDOW", "modelSettings")),
    ("H32", "tool search: unset/true = MCP tanımları ertelenir", ("ENABLE_TOOL_SEARCH",)),
    ("H36", "akış izleyicileri (watchdog) varsayılan AÇIK", ("CLAUDE_ENABLE_STREAM_WATCHDOG",)),
    ("H37", "MCP_TOOL_TIMEOUT ayarsız → çok uzun (~28 saat); sunucu başına timeout koy", ("MCP_TOOL_TIMEOUT",)),
    ("H16", "useAutoModeDuringPlan varsayılan AÇIK", ("useAutoModeDuringPlan",)),
]

# BEGIN VERIFIED (generated from docs corpus; do not edit by hand)
VERIFIED_SOURCE = 'code.claude.com/docs (221 sayfa, changelog v2.1.296) + kurulu 2.1.295, 2026-10-10'
VERIFIED_PAGES = {
    'effortLevel': ['settings-reference', 'env-vars'],
    'maxEffortLevel': ['settings-reference', 'env-vars'],
    'modelSettings': ['settings-reference', 'env-vars'],
    'fallbackModel': ['settings-reference', 'env-vars'],
    'advisorModel': ['settings-reference', 'env-vars'],
    'fastMode': ['settings-reference', 'agent-sdk__typescript'],
    'fastModePerSessionOptIn': ['settings-reference', 'fast-mode'],
    'CLAUDE_CODE_SUBAGENT_MODEL': ['env-vars', 'agent-teams'],
    'CLAUDE_CODE_SUBAGENT_MODEL_FORCE': ['env-vars', 'agent-teams'],
    'CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS': ['env-vars', 'agent-sdk__subagents'],
    'CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH': ['env-vars', 'agent-sdk__subagents'],
    'ultracode': ['settings-reference', 'commands'],
    'workflowKeywordTriggerEnabled': ['settings-reference'],
    'workflowSizeGuideline': ['settings-reference', 'changelog'],
    'CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS': ['env-vars', 'changelog'],
    'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS': ['env-vars', 'agent-teams'],
    'autoContinueAtUsageLimit': ['settings-reference', 'hooks'],
    'CLAUDE_CODE_GOAL_CHECKIN_MINUTES': ['env-vars', 'changelog'],
    'ENABLE_TOOL_SEARCH': ['env-vars', 'agent-sdk__tool-search'],
    'MCP_TOOL_TIMEOUT': ['env-vars', 'agent-sdk__mcp'],
    'MCP_TIMEOUT': ['env-vars', 'hooks'],
    'CLAUDE_CODE_MCP_STARTUP_WAIT_MS': ['env-vars', 'agent-sdk__mcp'],
    'MAX_MCP_OUTPUT_TOKENS': ['env-vars', 'agent-sdk__mcp'],
    'API_TIMEOUT_MS': ['env-vars', 'agent-sdk__python'],
    'CLAUDE_ENABLE_STREAM_WATCHDOG': ['env-vars', 'agent-sdk__python'],
    'CLAUDE_STREAM_IDLE_TIMEOUT_MS': ['env-vars', 'agent-sdk__python'],
    'promptCacheTtl': ['settings-reference', 'env-vars'],
    'subagentPromptCacheTtl': ['settings-reference', 'env-vars'],
    'DISABLE_PROMPT_CACHING*': ['env-vars', 'amazon-bedrock'],
    'CLAUDE_CODE_AUTO_COMPACT_WINDOW': ['settings-reference', 'env-vars'],
    'autoCompactWindow': ['settings-reference', 'env-vars'],
    'bashOutputMaxChars': ['settings-reference', 'env-vars'],
    'outputStyle': ['settings-reference', 'agent-sdk__configuration'],
    'permissions.defaultMode': ['settings-reference', 'hooks'],
    'permissions.disableAutoMode': ['settings-reference', 'admin-setup'],
    'autoMode.classifyAllShell': ['settings-reference', 'auto-mode-config'],
    'sandbox.allowUnsandboxedCommands': ['settings-reference', 'changelog'],
    'syncClaudeAiPlugins': ['settings-reference', 'admin-setup'],
    'syncClaudeAiSkills': ['settings-reference', 'admin-setup'],
    'skipWebFetchPreflight': ['settings-reference', 'claude-apps-gateway-deploy'],
    'ENABLE_CLAUDEAI_MCP_SERVERS': ['settings-reference', 'env-vars'],
    'strictMcpConfig': ['agent-sdk__claude-code-features', 'agent-sdk__typescript'],
    'CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT': ['env-vars', 'agent-sdk__modifying-system-prompts'],
    'CLAUDE_CODE_DISABLE_*': ['settings-reference', 'env-vars'],
    'CLAUDE_CODE_ENABLE_TODO_TOOLS': ['env-vars', 'agent-sdk__todo-tracking'],
    'worktree.sparsePaths': ['settings-reference', 'changelog'],
    'disableAllHooks': ['settings-reference', 'hooks'],
}
# END VERIFIED


# ---------------- shared helpers (imported by other HighPer scripts) ----------------
def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def claude_home(override=None):
    if override:
        return Path(override)
    return Path(os.environ["CLAUDE_CONFIG_DIR"]) if os.environ.get("CLAUDE_CONFIG_DIR") else Path.home() / ".claude"


def managed_path():
    if sys.platform == "win32":
        return Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ClaudeCode" / "managed-settings.json"
    if sys.platform == "darwin":
        return Path("/Library/Application Support/ClaudeCode/managed-settings.json")
    return Path("/etc/claude-code/managed-settings.json")


def load_sources(home, cwd):
    out = []
    for label, p in (("user", home / "settings.json"), ("project", cwd / ".claude" / "settings.json"),
                     ("local", cwd / ".claude" / "settings.local.json"), ("managed", managed_path())):
        out.append((label, p, read_json(p)))
    return out


def getpath(d, dotted):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def lookup(key, srcs, environ):
    """All (source, value) hits for a settings key or env var (env: settings `env` blocks + process)."""
    hits = []
    is_env = key.upper() == key
    for label, _, d in srcs:
        if not d:
            continue
        if is_env:
            env = d.get("env") or {}
            if key.endswith("*"):
                hits += [(f"{label}.env", f"{k}={v}") for k, v in env.items() if k.startswith(key[:-1])]
            elif key in env:
                hits.append((f"{label}.env", env[key]))
        else:
            v = getpath(d, key)
            if v is not None:
                hits.append((label, v))
    if is_env:
        if key.endswith("*"):
            hits += [("env", f"{k}={v}") for k, v in environ.items() if k.startswith(key[:-1])]
        elif key in environ:
            hits.append(("env", environ[key]))
    return hits


def installed_plugins(home):
    settings = read_json(home / "settings.json") or {}
    enabled = {k for k, v in (settings.get("enabledPlugins") or {}).items() if v}
    inst = (read_json(home / "plugins" / "installed_plugins.json") or {}).get("plugins") or {}
    out = []
    for name, recs in inst.items():
        for rec in recs:
            out.append({"name": name, "enabled": name in enabled, "path": rec.get("installPath", ""), "version": rec.get("version")})
    return out


def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"')
    return fm


def detect_tools(home):
    skills = home / "skills"
    settings = read_json(home / "settings.json") or {}
    plugins = " ".join((settings.get("enabledPlugins") or {}).keys()).lower()
    agents = {p.name for p in (home / "agents").glob("*.md")} if (home / "agents").is_dir() else set()
    return {
        "MinToken": (skills / "mintoken" / "SKILL.md").is_file(),
        "Headroom": bool(shutil.which("headroom")) or any(k.startswith("HEADROOM_") for k in os.environ),
        "Graphify": bool(shutil.which("graphify")) or (skills / "graphify").is_dir(),
        "Ponytail": any(skills.glob("ponytail*")) if skills.is_dir() else False,
        "claude-mem": "claude-mem" in plugins or (Path.home() / ".claude-mem").is_dir(),
        "everything-claude-code": "everything-claude-code" in plugins or {"planner.md", "architect.md", "code-reviewer.md"} <= agents,
        "SkillSpector": bool(shutil.which("skillspector")),
    }


def hooks_list(srcs, home):
    rows = []
    def scan(origin, hooks):
        for event, groups in (hooks or {}).items():
            for g in groups or []:
                for h in g.get("hooks", []):
                    rows.append({"origin": origin, "event": event, "matcher": g.get("matcher"), "type": h.get("type"),
                                 "command": str(h.get("command") or h.get("prompt") or "")[:90], "command_full": str(h.get("command") or h.get("prompt") or ""), "timeout": h.get("timeout")})
    for label, _, d in srcs:
        if d:
            scan(label, d.get("hooks"))
    for p in installed_plugins(home):
        if p["enabled"]:
            hj = read_json(Path(p["path"]) / "hooks" / "hooks.json")
            if hj:
                scan(f"plugin:{p['name']}", hj.get("hooks", hj))
    return rows


def agent_models(home, cwd, environ):
    """DZ-J4/H3: report how each custom agent's model resolves (frontmatter > env > main)."""
    env_model = environ.get("CLAUDE_CODE_SUBAGENT_MODEL")
    force = str(environ.get("CLAUDE_CODE_SUBAGENT_MODEL_FORCE", "")).lower() in ("1", "true")
    out = []
    for d in (home / "agents", cwd / ".claude" / "agents"):
        for p in sorted(d.glob("*.md")) if d.is_dir() else []:
            fm = frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            fm_model = fm.get("model")
            if force and env_model:
                res = f"{env_model} (CLAUDE_CODE_SUBAGENT_MODEL_FORCE)"
            elif fm_model and fm_model != "inherit":
                res = f"{fm_model} (frontmatter)"
            elif env_model:
                res = f"{env_model} (CLAUDE_CODE_SUBAGENT_MODEL)"
            else:
                res = "ana model (inherit)"
            out.append({"agent": p.stem, "resolved": res, "effort": fm.get("effort"), "tools": fm.get("tools") or "(kısıtsız)"})
    return out


def mcp_servers(home, cwd):
    cj = read_json(home.parent / ".claude.json") if home == claude_home() else read_json(home / ".claude.json")
    cj = cj or {}
    out = [("user", n, c) for n, c in (cj.get("mcpServers") or {}).items()]
    proj = (cj.get("projects") or {}).get(str(cwd).replace("\\", "/")) or {}
    out += [("local", n, c) for n, c in (proj.get("mcpServers") or {}).items()]
    out += [("project", n, c) for n, c in ((read_json(cwd / ".mcp.json") or {}).get("mcpServers") or {}).items()]
    return out


def audit(home, cwd, environ):
    srcs = load_sources(home, cwd)
    keys = []
    for k in CHECKLIST:
        hits = lookup(k, srcs, environ)
        known = k.rstrip("*") in VERIFIED_PAGES or k in VERIFIED_PAGES or k.endswith("*")
        keys.append({"key": k, "set": bool(hits), "values": hits, "known": known, "doc": VERIFIED_PAGES.get(k, [])})
    risks = []
    for k, h, cond, text, sugg, trade in RISKS:
        for src, v in lookup(k, srcs, environ):
            if cond(v):
                risks.append({"lever": h, "key": k, "value": v, "source": src, "risk": text, "suggest": sugg, "tradeoff": trade})
    style = None
    for _, _, d in srcs:
        if d and d.get("outputStyle"):
            style = d["outputStyle"]
    if style and str(style).lower() not in ("default", "explanatory", "learning", "concise"):
        risks.append({"lever": "H44", "key": "outputStyle", "value": style, "source": "settings",
                      "risk": "özel çıktı stili: keep-coding-instructions:true yoksa yerleşik kodlama talimatları düşer",
                      "suggest": "stil dosyasında keep-coding-instructions: true olduğunu doğrula", "tradeoff": "-"})
    servers = mcp_servers(home, cwd)
    if servers and not lookup("MCP_TOOL_TIMEOUT", srcs, environ) and not any(c.get("timeout") for _, _, c in servers):
        risks.append({"lever": "H37", "key": "MCP_TOOL_TIMEOUT", "value": None, "source": "-",
                      "risk": "MCP sunucuları var ama zaman aşımı yok (~28 saat): asılan çağrı oturumu bekletir",
                      "suggest": "sunucu başına timeout", "tradeoff": "uzun meşru çağrı kesilebilir"})
    set_keys = {k["key"] for k in keys if k["set"]}
    defaults = [(h, t) for h, t, ks in AT_DEFAULT if not (set(ks) & set_keys) and not any(lookup(x, srcs, environ) for x in ks)]
    return {
        "keys": keys, "risks": risks, "defaults": defaults, "tools": detect_tools(home),
        "plugins": installed_plugins(home), "hooks": hooks_list(srcs, home), "agents": agent_models(home, cwd, environ),
        "mcp": [{"scope": s, "name": n, "alwaysLoad": bool(c.get("alwaysLoad")), "timeout": c.get("timeout")} for s, n, c in servers],
        "managed": {"path": str(srcs[3][1]), "present": srcs[3][2] is not None},
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--home"); p.add_argument("--cwd")
    p.add_argument("--no-process-env", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="no-op: never writes")
    a = p.parse_args(argv)
    home = claude_home(a.home); cwd = Path(a.cwd or os.getcwd())
    r = audit(home, cwd, {} if a.no_process_env else dict(os.environ))
    if a.json:
        print(json.dumps(r, indent=1, default=str, ensure_ascii=False)); return 0
    print("=== (1) Performans riskleri (kanıt: ayar değeri) ===")
    if not r["risks"]:
        print("  ayarlarda performans riski bulunmadı")
    for x in r["risks"]:
        print(f"  {x['lever']:<8} {x['key']} = {json.dumps(x['value'], ensure_ascii=False)} [{x['source']}]\n"
              f"           risk: {x['risk']}\n           öneri: {x['suggest']} | takas: {x['tradeoff']}")
    print("\n=== (2) Kontrol listesi: VAR (ayarlı) ===")
    for k in r["keys"]:
        if k["set"]:
            vals = "; ".join(f"{v} [{s}]" for s, v in k["values"])
            mark = "" if k["known"] else "  (kurulu sürümde tanınmıyor olabilir)"
            print(f"  {k['key']}: {vals}{mark}")
    print(f"  YOK (varsayılanda): {sum(1 for k in r['keys'] if not k['set'])} anahtar — tam liste için --json")
    print("\n=== (3) Varsayılan nedeniyle etkin olanlar ===")
    for h, t in r["defaults"]:
        print(f"  {h:<9} {t}")
    print("\n=== (4) Kurulu araçlar (salt okunur tespit) ===")
    print("  " + " | ".join(f"{k}: {'VAR' if v else 'YOK'}" for k, v in r["tools"].items()))
    if r["tools"].get("MinToken"):
        print("  MinToken kurulu → çakışan önerilerde iki yön yan yana gösterilir (references/mintoken-interplay.md)")
    print(f"\n=== (5) Eklentiler ({len(r['plugins'])}), hook'lar ({len(r['hooks'])}), alt-ajanlar ({len(r['agents'])}), MCP ({len(r['mcp'])}) ===")
    for pl in r["plugins"]:
        print(f"  eklenti {pl['name']} v{pl['version']} {'etkin' if pl['enabled'] else 'kapalı'}")
    for h in r["hooks"]:
        print(f"  hook [{h['origin']}] {h['event']} matcher={h['matcher']!r} type={h['type']} timeout={h['timeout']}")
    for ag in r["agents"]:
        print(f"  alt-ajan {ag['agent']}: model → {ag['resolved']}; effort={ag['effort']}; tools={ag['tools']}")
    for m in r["mcp"]:
        print(f"  MCP [{m['scope']}] {m['name']} alwaysLoad={m['alwaysLoad']} timeout={m['timeout']}")
    print(f"\n=== (6) Yönetilen ayarlar: {'VAR' if r['managed']['present'] else 'yok/okunamadı'} ({r['managed']['path']}) — yalnız rapor ===")
    print(f"Anahtar adları: {VERIFIED_SOURCE}. Gerçek kaynaklar için /status; mod listesi için /plugin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
