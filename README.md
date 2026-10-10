# HighPer

A Claude Code skill that measures and improves how well Claude Code works: correct results, fewer wasted turns, shorter waits, fewer errors and retries, and more reliable long or unattended runs. It is the sister of [MinToken](https://github.com/omer-faruk-g/MinToken). MinToken lowers token use, HighPer raises quality and reliability. Each works on its own, and when their advice conflicts HighPer shows both sides instead of choosing for you.

- **Measure first, then suggest.** A lever (H1–H72) is suggested only after your own data shows the problem it fixes.
- **No promises in numbers.** No "X% faster", "2×" or "zero mistakes". You measure your own before and after, and the statistics tools tell you how much a small sample can show (rule of three, smallest detectable difference).
- **Nothing changes silently.** Changes to settings.json, hooks, CLAUDE.md, permissions, model or effort are shown as a diff and wait for your explicit approval. HighPer never commits or pushes on its own and never loosens permissions.
- **Labelled claims.** [D] official docs or Anthropic publication · [G] observed in a session · [R] third-party report, unverified · [I] inference, unverified.
- **Python standard library only, no network.** Every script supports `--help` and `--dry-run`. Session transcripts are read locally, and reports contain counters and durations only, never message text.

The skill itself (SKILL.md and references) is written in Turkish.

## Install

```bash
git clone https://github.com/omer-faruk-g/HighPer.git ~/.claude/skills/highper
```

Windows (PowerShell):

```powershell
git clone https://github.com/omer-faruk-g/HighPer.git "$env:USERPROFILE\.claude\skills\highper"
```

Claude Code picks the skill up automatically. It triggers when you say Claude Code is slow, stuck, making mistakes, answering late, or dropping long tasks halfway. You can also call it directly with `/highper`. Tested with Python 3.13; written for Python 3.7 or later.

## Commands

| Command | What it does |
|---|---|
| `/highper` | General audit plus a short baseline (`audit_perf.py`, `perf_baseline.py`) |
| `/highper hunt` | Inefficiency hunt: at most 10 findings, each with evidence, ordered correctness > reliability > latency > cost |
| `/highper plan <task>` | Sizes the task (XS/S/M/L) and suggests the verification steps and profile |
| `/highper review` | Prompt for an independent reviewer: fresh context, read-only, at most 2 rounds |
| `/highper measure` | Quality metrics, before/after comparison, smallest detectable difference |
| `/highper why-slow` | When quality or speed suddenly drops, checks the version, model, effort, plugins and the documented incident windows |
| `/highper route <task>` | Model and effort suggestion from five axes: ambiguity, scope, verifiability, risk, novelty |
| `/highper sentinel` | Regression sentinel: a fixed mini task set, logged per version, model and effort |
| `/highper zero` | Zero-Escape profile: lists every gate and its blind spots |
| `/highper escape-log` | Logs bugs found after delivery and reports the escape rate with an upper bound |
| `/highper report` | Markdown report: axis → finding → suggestion → trade-off → rollback |
| `/highper gradle` | Gradle/Fabric settings, version matrix draft, error blocks from logs |
| `/highper lint` | Lints CLAUDE.md, MEMORY.md and task prompts |

## Optional hooks (Zero-Escape gates)

Both hooks do nothing until a project contains its config file. Install them only after checking the schema against your Claude Code version's hooks page. Snippet for `~/.claude/settings.json` (replace `<HIGHPER>` with the skill path):

```json
{"hooks": {
  "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell",
                  "hooks": [{"type": "command", "command": "python \"<HIGHPER>/scripts/scope_guard.py\"", "timeout": 10}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python \"<HIGHPER>/scripts/verify_gate.py\"", "timeout": 900}]}]
}}
```

`<project>/.claude/highper-scope.json` is the scope guard. Writes outside `allow` or inside `deny` are blocked with exit code 2. It adds a restriction and never approves anything:

```json
{"allow": ["src/main/java/**", "src/main/resources/**"],
 "deny":  ["build/**", "run/**", ".gradle/**", "**/*.jar", "gradle/wrapper/**"]}
```

`<project>/.claude/highper-verify.json` is the "done" gate. Claude cannot end its turn until every command exits 0:

```json
{"commands": ["./gradlew compileJava -q", "./gradlew test -q"], "timeout_sec": 600, "budget_sec": 840}
```

Both hooks fail closed. An unreadable config file, an internal error, or a command that times out all block the action; a command that times out has its whole process tree killed. Keep `budget_sec` below the hook `timeout`, because if Claude Code kills the hook itself, the stop goes through unverified. Claude Code also ends the turn after 8 consecutive Stop blocks (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). In that case the delivery must be labelled "DOĞRULANMADI" (not verified).

Before delivery, `scripts/diff_audit.py` makes a read-only pass over the working tree and reports:
- out-of-scope changes;
- deleted or renamed files;
- generated or binary files;
- weakened tests, such as a removed assert or an added `@Disabled`;
- likely secrets;
- untracked files.

## What's inside

| Path | Purpose |
|---|---|
| `SKILL.md` | The rules Claude follows: principles, a 7-step workflow, the commands, hook snippets, delivery format |
| `references/` | 17 files: levers H1–H72, measurement protocol, Fabric/Gradle, quality multipliers, profiles, known incidents, model router, sentinel tasks, Zero-Escape profile, blind spots, statistical honesty, verification tables |
| `scripts/audit_perf.py` | Read-only audit of settings, env, plugins, hooks, MCP servers and subagent models |
| `scripts/perf_baseline.py` | Baseline from local transcripts: tool errors by class, repeated commands and reads, interruptions, idle gaps, compactions, API errors, turn durations |
| `scripts/hunt.py`, `dup_detect.py` | Inefficiency hunt; duplicate or overlapping skills, agents, commands and hooks |
| `scripts/claude_md_lint.py`, `task_prompt_lint.py` | Lint for instruction files and task prompts |
| `scripts/route_model.py`, `incident_check.py`, `pin_check.py` | Model suggestion; diagnosis of sudden regressions; version/model/effort pinning |
| `scripts/quality_score.py`, `sentinel.py`, `canary.py` | Quality metrics and statistics; regression and escape log; known-answer canary task |
| `scripts/scope_guard.py`, `verify_gate.py`, `diff_audit.py` | The Zero-Escape gates above |
| `scripts/gradle_perf.py`, `report.py` | Gradle/Fabric analysis; Markdown report (writes only to `--out`) |
| `tests/test_highper.py` | 42 tests, standard library only, temporary directories only |

```bash
python tests/test_highper.py
```

## Verification status

All 84 settings keys and env vars, and all 26 slash commands that HighPer names, were found in the Claude Code docs as checked on 2026-10-10. That check covered 221 pages and the changelog through v2.1.296, and was compared with installed CLI 2.1.295. The tables are in `references/scope-honesty.md`. Claude Code changes from version to version, so re-check after updates. Items labelled [R] or [I] stay unverified, and the skill says so wherever they appear. No gate guarantees zero escapes. `references/blind-spots.md` lists what each gate cannot catch.

## Türkçe özet

HighPer, Claude Code'un doğruluğunu, hızını ve güvenilirliğini ölçer. İyileştirme önerisini yalnız senin verinde sorun görüldüğünde yapar ve uygulamak için onayını bekler. Yüzde ya da "sıfır hata" vaadi vermez; önce/sonra farkını kendi ölçümünle görürsün. Sıfır Tolerans profili için iki hook vardır: kapsam bekçisi ve "bitti" kapısı. Proje klasöründe yapılandırma dosyası olmadıkça ikisi de hiçbir şey yapmaz. Kurulum için yukarıdaki `git clone` komutunu kullan.

## License

Copyright (C) 2026 Omer-F.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. It is distributed WITHOUT ANY WARRANTY. See [LICENSE](LICENSE) for the full text.
