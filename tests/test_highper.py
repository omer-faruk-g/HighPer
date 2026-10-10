#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""HighPer test suite — standard library only, no network.

    python tests/test_highper.py          (or: python -m unittest discover -s tests)

Every test works in a throw-away directory. Nothing under your real ~/.claude is read
for assertions or written. On Windows the temp dirs go under your home folder, because
Microsoft Store Python and MSIX apps see AppData through different virtual views
(override with HIGHPER_TEST_TMP).
"""
import hashlib
import importlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
for k in ("HIGHPER_SCOPE", "HIGHPER_VERIFY", "CLAUDE_CONFIG_DIR"):
    ENV.pop(k, None)
    os.environ.pop(k, None)


def tmpdir():
    base = os.environ.get("HIGHPER_TEST_TMP") or (str(Path.home()) if os.name == "nt" else None)
    return Path(tempfile.mkdtemp(prefix=".highper-test-", dir=base))


def rmtree(path):
    """shutil.rmtree that also removes read-only files (git objects on Windows)."""
    def fix(func, p, _exc):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    shutil.rmtree(path, **({"onexc": fix} if sys.version_info >= (3, 12) else {"onerror": fix}))


def run(script, *args, stdin=None, cwd=None, timeout=120):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], input=(stdin or "").encode("utf-8"),
                       capture_output=True, cwd=cwd, env=ENV, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def snapshot(*roots):
    out = {}
    for root in roots:
        for p in sorted(Path(root).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts:
                out[str(p)] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def jl(*objs):
    return "\n".join(json.dumps(o, ensure_ascii=False) for o in objs) + "\n"


def fake_home(root):
    """A minimal fake ~/.claude: settings, two overlapping skills, one transcript with known counters."""
    home = Path(root) / "claude-home"
    write(home / "settings.json", json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo a"}]}]}}))
    desc = "Measures and improves Claude Code performance, accuracy, speed and reliability for long tasks"
    write(home / "skills" / "alpha" / "SKILL.md", f"---\nname: alpha\ndescription: {desc}\n---\nbody\n")
    write(home / "skills" / "beta" / "SKILL.md", f"---\nname: beta\ndescription: {desc} quickly\n---\nbody\n")
    t0 = "2026-10-01T10:00:00.000Z"
    u = {"input_tokens": 10, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 50, "output_tokens": 20}
    lines = jl(
        {"type": "user", "timestamp": t0, "sessionId": "s1", "message": {"role": "user", "content": "add a handler"}},
        {"type": "assistant", "timestamp": "2026-10-01T10:00:05.000Z", "message": {"id": "msg_1", "model": "claude-opus-5-5", "usage": u,
         "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "a.py"}}]}},
        {"type": "user", "timestamp": "2026-10-01T10:00:06.000Z", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "File does not exist."}]}},
        {"type": "assistant", "timestamp": "2026-10-01T10:00:08.000Z", "message": {"id": "msg_2", "model": "claude-opus-5-5", "usage": u,
         "content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "a.py"}}]}},
        {"type": "user", "timestamp": "2026-10-01T10:00:09.000Z", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t2", "content": "ok"}]}},
        {"type": "assistant", "timestamp": "2026-10-01T10:00:10.000Z", "message": {"id": "msg_2", "model": "claude-opus-5-5", "usage": u,
         "content": [{"type": "text", "text": "done"}]}},
        {"type": "system", "subtype": "api_error", "timestamp": "2026-10-01T10:00:11.000Z"},
        {"type": "assistant", "isApiErrorMessage": True, "timestamp": "2026-10-01T10:00:11.000Z", "message": {"content": [{"type": "text", "text": "API Error"}]}},
        {"type": "user", "timestamp": "2026-10-01T10:00:12.000Z", "message": {"role": "user", "content": "[Request interrupted by user]"}},
        {"type": "user", "isCompactSummary": True, "timestamp": "2026-10-01T10:00:13.000Z", "message": {"role": "user", "content": "summary"}},
        {"type": "user", "timestamp": "2026-10-01T12:30:00.000Z", "sessionId": "s1", "message": {"role": "user", "content": "add a handler"}},
    )
    write(home / "projects" / "C--proj" / "11111111-aaaa-bbbb-cccc-000000000001.jsonl", lines)
    return home


# ---------------------------------------------------------------- structure
class Structure(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertTrue(m, "SKILL.md must start with YAML frontmatter")
        fm = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
        self.assertEqual(fm["name"].strip(), "highper")
        self.assertTrue(0 < len(fm["description"].strip()) <= 1024)
        self.assertLess(len(text.splitlines()), 500, "SKILL.md body should stay under 500 lines")

    def test_referenced_files_exist(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in set(re.findall(r"`?(?:references/)?([a-z0-9-]+\.md)`", text)):
            self.assertTrue((ROOT / "references" / name).is_file(), name)
        for name in set(re.findall(r"([a-z_]+\.py)", text)):
            self.assertTrue((SCRIPTS / name).is_file(), name)
        self.assertEqual(len(list((ROOT / "references").glob("*.md"))), 17)
        self.assertEqual(len(list(SCRIPTS.glob("*.py"))), 17)

    def test_scripts_compile_without_warnings(self):
        for p in sorted(SCRIPTS.glob("*.py")):
            with warnings.catch_warnings():
                warnings.simplefilter("error")  # e.g. invalid escape sequences become errors
                compile(p.read_text(encoding="utf-8"), str(p), "exec")

    def test_stdlib_only(self):
        stdlib = set(getattr(sys, "stdlib_module_names", ())) | {s.stem for s in SCRIPTS.glob("*.py")}
        if not getattr(sys, "stdlib_module_names", None):
            self.skipTest("needs Python 3.10+ for sys.stdlib_module_names")
        for p in SCRIPTS.glob("*.py"):
            for mod in re.findall(r"^\s*(?:import|from)\s+([a-zA-Z_]\w*)", p.read_text(encoding="utf-8"), re.M):
                self.assertIn(mod, stdlib, f"{p.name} imports non-stdlib module {mod}")

    def test_no_network_calls(self):
        for p in SCRIPTS.glob("*.py"):
            src = p.read_text(encoding="utf-8")
            self.assertNotRegex(src, r"\b(urllib\.request|http\.client|socket\.|requests\.)", p.name)

    def test_help_and_license_header(self):
        for p in sorted(SCRIPTS.glob("*.py")):
            code, out, err = run(p.name, "--help")
            self.assertEqual(code, 0, f"{p.name} --help: {err[-300:]}")
            self.assertTrue(out.strip(), p.name)
            self.assertIn("SPDX-License-Identifier: GPL-3.0-or-later", p.read_text(encoding="utf-8")[:300], p.name)


# ---------------------------------------------------------------- read-only scripts
class ReadOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tmpdir()
        self.home = fake_home(self.tmp)
        self.proj = self.tmp / "proj"
        write(self.proj / "CLAUDE.md", "# Rules\n" + "".join(f"- rule {i}\n" for i in range(230)))
        write(self.proj / "fabric.mod.json", '{"id": "x"}')
        write(self.proj / "gradle.properties", "minecraft_version=1.21.1\nloader_version=0.16.5\n")
        write(self.proj / "build.gradle", "plugins { id 'fabric-loom' version '1.7-SNAPSHOT' }\n")
        write(self.proj / "run" / "logs" / "latest.log", "".join(f"[INFO] line {i}\n" for i in range(300))
              + "[ERROR] Mixin apply failed\njava.lang.RuntimeException: boom\n\tat a.b.C.d(C.java:1)\n")

    def tearDown(self):
        rmtree(self.tmp)

    def test_scripts_never_write(self):
        before = snapshot(self.home, self.proj)
        h, c = ("--home", self.home), ("--cwd", self.proj)
        calls = [("audit_perf.py", *h, *c, "--no-process-env"), ("audit_perf.py", *h, *c, "--json"),
                 ("perf_baseline.py", "--projects", self.home / "projects"), ("hunt.py", *h, *c),
                 ("dup_detect.py", *h, *c), ("incident_check.py", *h), ("claude_md_lint.py", *c, *h),
                 ("gradle_perf.py", self.proj), ("gradle_perf.py", "--tail-errors", self.proj / "run/logs/latest.log"),
                 ("pin_check.py", *h, *c), ("report.py", *h, *c), ("route_model.py", "--ambiguity", 1, "--scope", 1, "--verifiability", 0, "--risk", 2, "--novelty", 0),
                 ("task_prompt_lint.py", "fix it"), ("quality_score.py", "--min-detectable", "20"),
                 ("canary.py", "prompt"), ("sentinel.py", "template")]
        for call in calls:
            code, out, err = run(*call, cwd=self.proj)
            self.assertEqual(code, 0, f"{call[0]}: {err[-400:]}")
            self.assertTrue(out.strip(), f"{call[0]} printed nothing")
        self.assertEqual(before, snapshot(self.home, self.proj), "a read-only script changed a file")

    def test_baseline_counters(self):
        code, out, err = run("perf_baseline.py", "--projects", self.home / "projects", "--json")
        self.assertEqual(code, 0, err)
        t = json.loads(out)["total"]
        expect = {"tool_calls": 2, "tool_errors": 1, "api_requests": 2, "api_errors": 1, "repeat_read": 1,
                  "interruptions": 1, "compactions": 1, "user_turns": 2, "repeat_prompts": 1, "idle_gaps_over_1h": 1}
        for k, v in expect.items():
            self.assertEqual(t.get(k), v, f"{k}: {t}")

    def test_baseline_prints_no_message_text(self):
        code, out, _ = run("perf_baseline.py", "--projects", self.home / "projects", "--json")
        for secret_text in ("add a handler", "File does not exist", "summary"):
            self.assertNotIn(secret_text, out)

    def test_dup_detect_finds_overlap(self):
        code, out, err = run("dup_detect.py", "--home", self.home, "--cwd", self.proj, "--json")
        self.assertEqual(code, 0, err)
        pairs = json.loads(out)["overlapping_descriptions"]
        self.assertTrue(any("alpha" in p["a"] + p["b"] and "beta" in p["a"] + p["b"] for p in pairs), pairs)

    def test_claude_md_size_warning(self):
        code, out, _ = run("claude_md_lint.py", self.proj / "CLAUDE.md")
        self.assertEqual(code, 0)
        self.assertIn(">200", out)

    def test_gradle_fabric_detected_and_log_filtered(self):
        code, out, err = run("gradle_perf.py", self.proj, "--json")
        self.assertEqual(code, 0, err)
        self.assertTrue(json.loads(out)["fabric"])
        code, out, _ = run("gradle_perf.py", "--tail-errors", self.proj / "run/logs/latest.log")
        self.assertIn("Mixin apply failed", out)
        self.assertNotIn("line 100\n", out)

    def test_task_prompt_lint(self):
        _, vague, _ = run("task_prompt_lint.py", "fix it")
        good = ("src/main/java/x/Handler.java icinde event handler ekle; ExistingHandler.java gibi yaz. "
                "Basari: ./gradlew compileJava 0 ile cikmali, `./gradlew test --tests '*Handler*'` gecmeli. "
                "build/, run/, gradle/wrapper/ dosyalarina dokunma. Kaynak: gradle dependencies.")
        _, ok, _ = run("task_prompt_lint.py", good)
        self.assertGreater(vague.count("✗"), ok.count("✗"))

    def test_route_model_monotonic(self):
        _, low, _ = run("route_model.py", "--ambiguity", 0, "--scope", 0, "--verifiability", 0, "--risk", 0, "--novelty", 0)
        _, high, _ = run("route_model.py", "--ambiguity", 2, "--scope", 2, "--verifiability", 2, "--risk", 2, "--novelty", 2)
        self.assertIn("Sonnet", low.split("ÖNERİ:")[1].splitlines()[0])
        self.assertIn("Opus", high.split("ÖNERİ:")[1].splitlines()[0])


# ---------------------------------------------------------------- statistics
class Statistics(unittest.TestCase):
    def test_rule_of_three(self):
        _, out, _ = run("quality_score.py", "--escapes", 0, "--deliveries", 40)
        self.assertIn("7.5", out)
        self.assertIn("sıfır risk", out)  # stated as NOT zero risk

    def test_min_detectable(self):
        _, out, _ = run("quality_score.py", "--min-detectable", 10)
        self.assertIn("63%", out)  # 2.8 * sqrt(2 * 0.25 / 10) = 0.626

    def test_compare_and_ceiling(self):
        tmp = tmpdir()
        try:
            rows = "condition,task_id,first_try_pass,fix_rounds\n" + "".join(
                f"baseline,t{i},{1 if i < 6 else 0},1\nhighper,t{i},{1 if i < 8 else 0},0\n" for i in range(10))
            f = write(tmp / "r.csv", rows)
            code, out, err = run("quality_score.py", f, "--compare", "baseline", "highper")
            self.assertEqual(code, 0, err)
            self.assertIn("2×", out)
        finally:
            rmtree(tmp)


# ---------------------------------------------------------------- scope_guard (O3)
class ScopeGuard(unittest.TestCase):
    CFG = {"allow": ["src/main/java/**", "src/main/resources/**", "notes/**"],
           "deny": ["build/**", "run/**", ".gradle/**", "**/*.jar", "gradle/wrapper/**"]}

    def setUp(self):
        self.sg = importlib.import_module("scope_guard")
        self.tmp = tmpdir()
        write(self.tmp / ".claude" / "highper-scope.json", json.dumps(self.CFG))

    def tearDown(self):
        rmtree(self.tmp)

    def decide(self, tool, **inp):
        return self.sg.decide({"tool_name": tool, "tool_input": inp, "cwd": str(self.tmp)})[0]

    def test_file_tools(self):
        self.assertTrue(self.decide("Write", file_path=str(self.tmp / "src/main/java/A.java")))
        self.assertTrue(self.decide("Edit", file_path="src/main/resources/fabric.mod.json"))
        self.assertFalse(self.decide("Write", file_path=str(self.tmp / "build/x.txt")))
        self.assertFalse(self.decide("Edit", file_path="README.md"))  # not in allow-list
        self.assertFalse(self.decide("Write", file_path=str(self.tmp.parent / "elsewhere.txt")))
        self.assertFalse(self.decide("MultiEdit", file_path="src/main/java/../../../build.gradle"))
        self.assertFalse(self.decide("NotebookEdit", notebook_path="run/a.ipynb"))
        self.assertIsNone(self.decide("Read", file_path="build/x"))  # reads are not this hook's job

    def test_bash_targets(self):
        blocked = ["echo hi > build/out.txt", "./gradlew build 2>&1 | tee run/log.txt", "cp a.jar gradle/wrapper/x.jar",
                   "sed -i 's/a/b/' build.gradle", "ls && rm -rf .gradle/caches", "mv src/main/java/A.java libs/A.jar",
                   "touch notes/ok.txt; echo x >> README.md", "echo a &> run/all.log", "sudo tee build/x < in.txt"]
        allowed = ['echo "a > b"; ls', "git status && echo ok", "./gradlew compileJava -q 2>&1 | head -50",
                   "cat build/log.txt | grep ERROR", "echo hi > notes/n.txt", "grep -rn x src > /dev/null",
                   "echo 'rm build/x' ", "python -c \"print('> build')\""]
        for cmd in blocked:
            self.assertFalse(self.decide("Bash", command=cmd), cmd)
        for cmd in allowed:
            self.assertTrue(self.decide("Bash", command=cmd), cmd)

    def test_powershell(self):
        self.assertFalse(self.decide("PowerShell", command="Set-Content -Path build/x.txt -Value 1"))
        self.assertFalse(self.decide("PowerShell", command="Remove-Item run/logs -Recurse"))
        self.assertTrue(self.decide("PowerShell", command="Get-Content build/x.txt | Select-Object -First 5"))

    def test_no_config_is_noop(self):
        empty = tmpdir()
        try:
            r = self.sg.decide({"tool_name": "Write", "tool_input": {"file_path": "build/x"}, "cwd": str(empty)})
            self.assertIsNone(r[0])
        finally:
            rmtree(empty)

    def test_broken_config_fails_closed(self):
        write(self.tmp / ".claude" / "highper-scope.json", "{broken")
        self.assertFalse(self.decide("Write", file_path="src/main/java/A.java"))

    def test_globs(self):
        g = self.sg.glob_re
        self.assertTrue(g("**/*.jar").match("a/b/c.jar") and g("**/*.jar").match("c.jar"))
        self.assertFalse(g("src/*.java").match("src/a/B.java"))
        self.assertTrue(g("src/**").match("src/a/B.java"))

    def test_hook_protocol(self):
        ev = {"tool_name": "Write", "tool_input": {"file_path": "build/x"}, "cwd": str(self.tmp), "hook_event_name": "PreToolUse"}
        code, out, err = run("scope_guard.py", stdin=json.dumps(ev))
        self.assertEqual(code, 2)
        self.assertIn("YASAK", err)
        self.assertEqual(out, "", "must never print an allow/deny JSON decision")
        ev["tool_input"]["file_path"] = "src/main/java/A.java"
        self.assertEqual(run("scope_guard.py", stdin=json.dumps(ev))[:2], (0, ""))
        self.assertEqual(run("scope_guard.py", stdin="not json")[:2], (0, ""))

    def test_internal_error_fails_closed(self):
        ev = {"tool_name": "Write", "tool_input": {"file_path": None}, "cwd": str(self.tmp)}
        code, out, err = run("scope_guard.py", stdin=json.dumps(ev))
        self.assertEqual(code, 2, err)
        self.assertIn("iç hata", err)


# ---------------------------------------------------------------- verify_gate (O2)
class VerifyGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tmpdir()

    def tearDown(self):
        rmtree(self.tmp)

    def gate(self, commands, timeout=60, *extra):
        write(self.tmp / ".claude" / "highper-verify.json", json.dumps({"commands": commands, "timeout_sec": timeout}))
        return run("verify_gate.py", *extra, stdin=json.dumps({"cwd": str(self.tmp), "stop_hook_active": False}))

    def test_no_config(self):
        self.assertEqual(run("verify_gate.py", stdin=json.dumps({"cwd": str(self.tmp)}))[:2], (0, ""))

    def test_pass_is_silent(self):
        self.assertEqual(self.gate(["exit 0", "exit 0"])[:2], (0, ""))

    def test_fail_blocks(self):
        code, out, _ = self.gate(["exit 0", "exit 3"])
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        self.assertIn("çıkış kodu 3", d["reason"])
        self.assertIn("DOĞRULANMADI", d["reason"])

    def test_timeout_blocks_and_returns(self):
        py = sys.executable.replace("\\", "/")
        t = time.time()
        code, out, _ = self.gate([f'"{py}" -c "import time; time.sleep(30)"'], 2)
        self.assertLess(time.time() - t, 20, "gate must not wait for a hung command past its timeout")
        self.assertEqual(json.loads(out)["decision"], "block")
        self.assertIn("124", json.loads(out)["reason"])

    def test_broken_config_blocks(self):
        write(self.tmp / ".claude" / "highper-verify.json", "{broken")
        code, out, _ = run("verify_gate.py", stdin=json.dumps({"cwd": str(self.tmp)}))
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_total_budget(self):
        write(self.tmp / ".claude" / "highper-verify.json",
              json.dumps({"commands": ["exit 0", "exit 0"], "timeout_sec": 60, "budget_sec": 0}))
        _, out, _ = run("verify_gate.py", stdin=json.dumps({"cwd": str(self.tmp)}))
        self.assertIn("bütçe", json.loads(out)["reason"])

    def test_dry_run_runs_nothing(self):
        code, out, _ = self.gate(["touch made_by_gate"], 60, "--dry-run")
        self.assertIn("touch made_by_gate", out)
        self.assertFalse((self.tmp / "made_by_gate").exists())


# ---------------------------------------------------------------- diff_audit (O4)
@unittest.skipUnless(shutil.which("git"), "git not installed")
class DiffAudit(unittest.TestCase):
    def git(self, *a):
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *a], check=True, capture_output=True)

    def setUp(self):
        self.tmp = tmpdir()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        write(self.repo / "src/main/java/A.java", "class A {\n  int f() { return 1; }\n}\n")
        write(self.repo / "src/test/java/ATest.java", "class ATest {\n  @Test void t() {\n    assertEquals(1, new A().f());\n  }\n}\n")
        write(self.repo / "README.md", "readme\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        # changes: weaken the test, add a secret + TODO, delete README, untracked file with a token
        write(self.repo / "src/test/java/ATest.java", "class ATest {\n  @" + "Disabled @Test void t() {\n  }\n}\n")
        key = "api" + "Key"  # built at runtime so this file itself never looks like a secret
        write(self.repo / "src/main/java/A.java", f'class A {{\n  String {key} = "abcdef123456";\n  // TODO later\n  int f() {{ return 1; }}\n}}\n')
        (self.repo / "README.md").unlink()
        write(self.repo / "notes.txt", "token: " + "gh" + "p_" + "A" * 36 + "\n")

    def tearDown(self):
        rmtree(self.tmp)

    def test_findings(self):
        idx = self.repo / ".git" / "index"
        before = idx.read_bytes()
        code, out, err = run("diff_audit.py", "--repo", self.repo, "--expect", "src/main/java/**", "--json")
        self.assertEqual(code, 0, err)
        r = json.loads(out)
        c = r["correctness"]
        self.assertTrue(any(x.startswith("src/test/java/ATest.java") for x in c["(e) zayıflatılmış test"]), c)
        self.assertIn("src/main/java/A.java", c["(f) gizli bilgi şüphesi"])
        self.assertIn("notes.txt", c["(f) gizli bilgi şüphesi"])
        self.assertIn("README.md", c["(c) silinen"])
        self.assertIn("notes.txt", c["(b) kabul ölçütü dışında değişiklik"])
        self.assertNotIn("src/main/java/A.java", c["(b) kabul ölçütü dışında değişiklik"])
        self.assertIn("src/main/java/A.java", r["optional"]["eklenen TODO/FIXME"])
        self.assertEqual(before, idx.read_bytes(), "diff_audit must not touch the git index")

    def test_secret_regex(self):
        da = importlib.import_module("diff_audit")
        self.assertIsNone(da.SECRET.search('x(mintoken="aynı yön (MinToken B4)")'))
        self.assertTrue(da.SECRET.search("api_token = " + "'abcdefgh1'"))  # split so this file is not flagged
        self.assertTrue(da.SECRET.search('PASSWORD: ' + '"hunter22"'))

    def test_scope_config_used(self):
        write(self.repo / ".claude" / "highper-scope.json", json.dumps({"allow": ["src/**"], "deny": []}))
        _, out, _ = run("diff_audit.py", "--repo", self.repo, "--json")
        self.assertIn("notes.txt", json.loads(out)["correctness"]["(a) kapsam dışı/yasak"])

    def test_not_a_repo(self):
        plain = tmpdir()
        try:
            self.assertEqual(run("diff_audit.py", "--repo", plain)[0], 1)
        finally:
            rmtree(plain)


# ---------------------------------------------------------------- writers: only where told
class Writers(unittest.TestCase):
    def setUp(self):
        self.tmp = tmpdir()
        self.home = fake_home(self.tmp)

    def tearDown(self):
        rmtree(self.tmp)

    def test_report_only_to_out(self):
        before = snapshot(self.tmp)
        code, out, err = run("report.py", "--home", self.home, "--cwd", self.tmp)
        self.assertEqual(code, 0, err)
        self.assertEqual(before, snapshot(self.tmp))
        dest = self.tmp / "r.md"
        self.assertEqual(run("report.py", "--home", self.home, "--cwd", self.tmp, "--out", dest)[0], 0)
        after = snapshot(self.tmp)
        self.assertEqual(set(after) - set(before), {str(dest)})
        self.assertIn("#", dest.read_text(encoding="utf-8"))

    def test_sentinel_store(self):
        store = self.tmp / "s.json"
        args = ("add", "--store", store, "--task", "T1", "--first-try-pass", 1, "--fix-rounds", 0, "--minutes", 7.5)
        self.assertEqual(run("sentinel.py", *args, "--dry-run", cwd=self.tmp)[0], 0)
        self.assertFalse(store.exists(), "--dry-run must not write")
        self.assertEqual(run("sentinel.py", *args, cwd=self.tmp)[0], 0)
        self.assertEqual(len(json.loads(store.read_text(encoding="utf-8"))["runs"]), 1)
        run("sentinel.py", "escape", "--store", store, "--gate", "test", "--cls", "logic", "--would-catch", "review", cwd=self.tmp)
        _, out, _ = run("sentinel.py", "escapes", "--store", store, cwd=self.tmp)
        self.assertIn("1", out)
        _, out, err = run("sentinel.py", "compare", "--store", store, "--by", "model", cwd=self.tmp)
        self.assertTrue(out.strip(), err)

    def test_pin_snapshot_roundtrip(self):
        snap = self.tmp / "pins.json"
        h = ("--home", self.home, "--cwd", self.tmp)
        self.assertEqual(run("pin_check.py", *h, "--snapshot", snap, "--dry-run")[0], 0)
        self.assertFalse(snap.exists(), "--dry-run must not write")
        self.assertEqual(run("pin_check.py", *h, "--snapshot", snap)[0], 0)
        self.assertTrue(snap.is_file())
        code, out, err = run("pin_check.py", *h, "--compare", snap)
        self.assertEqual(code, 0, err)
        s = json.loads(snap.read_text(encoding="utf-8"))
        s["model"] = "something-else"
        snap.write_text(json.dumps(s), encoding="utf-8")
        _, out2, _ = run("pin_check.py", *h, "--compare", snap)
        self.assertNotEqual(out, out2, "a changed pin must be reported")


# ---------------------------------------------------------------- canary (O10)
class Canary(unittest.TestCase):
    GOOD = ("def rle(s):\n    out, i = [], 0\n    while i < len(s):\n        j = i\n"
            "        while j < len(s) and s[j] == s[i]:\n            j += 1\n"
            "        out.append(f'{j - i}{s[i]}')\n        i = j\n    return ''.join(out)\n")

    def setUp(self):
        self.tmp = tmpdir()

    def tearDown(self):
        rmtree(self.tmp)

    def test_without_yes_nothing_runs(self):
        write(self.tmp / "highper_canary.py", "open('EXECUTED', 'w').close()\n")
        self.assertEqual(run("canary.py", "check", "--dir", self.tmp, cwd=self.tmp)[0], 0)
        self.assertFalse((self.tmp / "EXECUTED").exists())

    def test_good_and_bad(self):
        write(self.tmp / "highper_canary.py", self.GOOD)
        self.assertEqual(run("canary.py", "check", "--dir", self.tmp, "--yes", cwd=self.tmp)[0], 0)
        write(self.tmp / "highper_canary.py", self.GOOD.replace("j - i", "j - i - 1"))
        self.assertEqual(run("canary.py", "check", "--dir", self.tmp, "--yes", cwd=self.tmp)[0], 1)

    def test_check_text(self):
        self.assertEqual(run("canary.py", "check-text", write(self.tmp / "ok.txt", "All tests passed."))[0], 0)
        self.assertEqual(run("canary.py", "check-text", write(self.tmp / "bad.txt", "All tests ผ passed."))[0], 1)
        self.assertEqual(run("canary.py", "check-text", write(self.tmp / "empty.txt", "  \n"))[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
