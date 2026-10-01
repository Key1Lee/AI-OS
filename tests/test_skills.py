from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from py_dev.config import ModelSettings
from py_dev.capabilities import skill_capability_matrix
from py_dev.local_runtime import LocalRuntimeError, LocalRuntimeReport
from py_dev.models import ProviderResult
from py_dev.runtime import AIOSRuntime
from py_dev.runtime_config import RuntimeConfigResolver
from py_dev.skill_audit import audit
from py_dev.skill_state import SkillInterviewStore, SkillStateError, save_context
from py_dev.skills import SkillCatalog, SkillError, SkillRunner
from py_dev.source_registry import SourceRegistry, SourceRegistryError


ROOT = Path(__file__).resolve().parents[1]


def fake_report() -> LocalRuntimeReport:
    return LocalRuntimeReport(
        Path("/tmp/Qwen3-4B-Q4_K_M.gguf"), "Qwen3-4B-Q4_K_M.gguf", "Q4_K_M",
        "Qwen3-4B-Q4_K_M", {"n_ctx_train": 40960}, Path("/tmp/llama-server"),
        "version: test", ("MTL0: test",), "auto", 99, True,
        32768, 40960, "http://127.0.0.1:8080/v1", True, False, True, False,
    )


class FakeProvider:
    def __init__(self, name: str):
        self.name = name
        self.model = f"test-{name}"
        self.calls = []

    def available(self):
        return True

    def generate(self, request):
        self.calls.append(request)
        return ProviderResult("One question?", self.model, "stop", 1, {"prompt_tokens": 10, "completion_tokens": 3})


class SkillCatalogTests(unittest.TestCase):
    def test_every_skill_has_direct_indirect_incomplete_edge_and_negative_cases(self):
        catalog = SkillCatalog()
        for name in catalog.skills:
            with (ROOT / "skills" / name / "tests" / "cases.toml").open("rb") as stream:
                cases = tomllib.load(stream)
            for kind in ("direct", "indirect", "incomplete", "edge"):
                self.assertEqual(catalog.resolve(cases[kind]).name, name, (name, kind))
            self.assertIsNone(catalog.resolve(cases["non_activation"]), name)

    def test_audit_architecture_routing_and_adjacent_workflows(self):
        catalog = SkillCatalog()
        with (ROOT / "evals" / "audit-cases.toml").open("rb") as stream:
            cases = tomllib.load(stream)["scenario"]
        for case in cases:
            resolved = catalog.resolve(case["request"])
            self.assertEqual(resolved.name if resolved else "native", case["route"], case["id"])

    def test_audit_script_imports_from_canonical_and_generated_locations(self):
        for base in ("skills", ".agents/skills", ".claude/skills"):
            script = ROOT / base / "audit" / "scripts" / "check.py"
            result = subprocess.run(
                [sys.executable, str(script), "--help"], cwd="/tmp", capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, (script, result.stderr))

    def test_unknown_and_ambiguous_commands_fail(self):
        catalog = SkillCatalog()
        with self.assertRaises(SkillError):
            catalog.resolve("$unknown")
        with self.assertRaises(SkillError):
            catalog.resolve("Audit my AI OS and grill me on a plan")
        self.assertIsNone(catalog.resolve("Do not use $audit; just summarize this file"))

    def test_skills_use_semantic_profiles_and_valid_references(self):
        catalog = SkillCatalog()
        resolver = RuntimeConfigResolver()
        for skill in catalog.skills.values():
            config = resolver.resolve(task=skill.task_profile)
            self.assertEqual(config.get("runtime", "provider"), "qwen_local")
            self.assertIn(config.get("reasoning", "default"), {"low", "medium", "high"})
            self.assertLessEqual(len(skill.description), 180)
            for relative in __import__("re").findall(r"\]\((references/[^)]+)\)", skill.instructions):
                self.assertTrue((skill.path.parent / relative).is_file(), (skill.name, relative))

    def test_provider_capability_matrix_is_configured_and_permission_free(self):
        matrix = skill_capability_matrix(ModelSettings(), fake_report())
        self.assertTrue(matrix["qwen_local"]["eligible"])
        self.assertTrue(matrix["qwen_local"]["availability_verified"])
        self.assertEqual(matrix["qwen_local"]["context_limit"], 32768)
        self.assertTrue(matrix["qwen_local"]["thinking_control"])
        self.assertFalse(matrix["openai"]["eligible"])
        self.assertFalse(matrix["claude"]["eligible"])
        self.assertFalse(any(item["tool_authority"] for item in matrix.values()))

    def test_generated_mirrors_match_single_canonical_source(self):
        for name in SkillCatalog().skills:
            source = (ROOT / "skills" / name / "SKILL.md").read_bytes()
            for mirror in (".agents", ".claude"):
                self.assertEqual(source, (ROOT / mirror / "skills" / name / "SKILL.md").read_bytes())


class SkillRunnerTests(unittest.TestCase):
    def setUp(self):
        self.qwen = FakeProvider("qwen_local")
        self.openai = FakeProvider("openai")
        self.runtime = AIOSRuntime(
            base_settings=ModelSettings(openai_enabled=True, openai_model="configured", cloud_call_budget=1),
            local_probe=lambda config: fake_report(),
            providers={"qwen_local": self.qwen, "openai": self.openai, "claude": FakeProvider("claude")},
            trace_sink=lambda trace: None, audit_sink=lambda event: None,
        )
        self.runner = SkillRunner(self.runtime)

    def test_skill_instructions_profile_and_provider_route_to_qwen(self):
        execution = self.runner.run("$link register a source", overrides={"reasoning": "none", "max_output": 64})
        self.assertEqual(execution.skill.name, "link")
        self.assertEqual(execution.skill.task_profile, "skill_link")
        self.assertEqual(execution.result.response.provider, "qwen_local")
        self.assertIn("Register", self.qwen.calls[0].system_instructions)
        self.assertEqual(self.qwen.calls[0].task_type, "skill_link")
        self.assertFalse(self.openai.calls)

    def test_unmatched_normal_task_uses_qwen_without_a_skill(self):
        execution = self.runner.run("Summarize this short note", overrides={"reasoning": "none", "max_output": 64})
        self.assertIsNone(execution.skill)
        self.assertEqual(execution.result.response.provider, "qwen_local")

    def test_project_and_run_provider_overrides_do_not_change_skill(self):
        execution = self.runner.run("$level-up my AI OS", project="Toptal-Testing", overrides={"provider": "openai", "max_output": 64})
        self.assertEqual(execution.skill.name, "level-up")
        self.assertEqual(execution.result.response.provider, "openai")
        self.assertEqual(execution.result.config.source("runtime", "provider"), "run")
        self.assertFalse(self.qwen.calls)

    def test_project_audit_profile_can_select_optional_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / "config", root / "config")
            shutil.copytree(ROOT / "skills", root / "skills")
            project = root / "projects" / "Example"
            project.mkdir(parents=True)
            (project / "aios.toml").write_text('inherits = ["global"]\n[task_profiles.skill_audit]\nprovider = "openai"\n')
            runtime = AIOSRuntime(
                resolver=RuntimeConfigResolver(root),
                base_settings=ModelSettings(openai_enabled=True, openai_model="configured", cloud_call_budget=1),
                local_probe=lambda config: fake_report(),
                providers={"qwen_local": self.qwen, "openai": self.openai, "claude": FakeProvider("claude")},
                trace_sink=lambda trace: None, audit_sink=lambda event: None,
            )
            with patch("py_dev.skill_audit.audit", return_value={"findings": []}):
                result = SkillRunner(runtime, SkillCatalog(root)).run("$audit", project="Example", overrides={"max_output": 64})
            self.assertEqual(result.result.response.provider, "openai")
            self.assertEqual(result.result.config.source("runtime", "provider"), "task:skill_audit")

    def test_stronger_reasoning_does_not_grant_tools(self):
        with patch("py_dev.skill_audit.audit", return_value={"findings": []}):
            with self.assertRaisesRegex(ValueError, "authorization"):
                self.runner.run("$audit", overrides={"reasoning": "xhigh", "tools": ["filesystem_write"]})
        self.assertFalse(self.qwen.calls)

    def test_grill_session_checkpoints_and_resumes_outside_model_context(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            first = self.runner.run("$grill-me about an idea", overrides={"reasoning": "none", "max_output": 64})
            self.assertIsNotNone(first.session_id)
            second = self.runner.run("Continue $grill-me", session_id=first.session_id, answer="A local tool", question="What is the idea?", overrides={"reasoning": "none", "max_output": 64})
            record = SkillInterviewStore(ROOT).get(None, first.session_id)
            self.assertEqual(record["answers"][0]["answer"], "A local tool")
            self.assertEqual(second.session_id, first.session_id)
            self.assertNotIn("A local tool", repr(second.result.trace))

    def test_incomplete_grill_request_asks_for_topic_before_guessing(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            self.runner.run("$grill-me", overrides={"reasoning": "none", "max_output": 64})
            self.assertIn("have not provided a topic", self.qwen.calls[-1].messages[-1]["content"])

    def test_audit_evidence_is_supplied_by_application(self):
        evidence = {"scope": "global", "live": True, "passed": ["AUD-001"], "findings": []}
        with patch("py_dev.skill_audit.audit", return_value=evidence):
            self.runner.run("$audit", overrides={"reasoning": "none", "max_output": 64})
        self.assertIn("AUD-001", str(self.qwen.calls[-1].context))

    def test_local_qwen_discovers_linked_route_without_loading_source_body(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            target = Path(folder) / "revenue-dashboard.txt"
            target.write_text("PRIVATE REVENUE BODY")
            SourceRegistry(ROOT).register(str(target), "Revenue dashboard", source_id="revenue-dashboard")
            other = Path(folder) / "hiring-plan.txt"
            other.write_text("OTHER PRIVATE BODY")
            SourceRegistry(ROOT).register(str(other), "Hiring plan", source_id="hiring-plan")
            self.runner.run("Where is the revenue dashboard?", overrides={"reasoning": "none", "max_output": 64})
            context = str(self.qwen.calls[-1].context)
            self.assertIn("revenue-dashboard", context)
            self.assertNotIn("hiring-plan", context)
            self.assertNotIn("PRIVATE REVENUE BODY", context)
            self.runner.run("Where is the revenue dashboard?", overrides={"provider": "openai", "max_output": 64})
            self.assertNotIn("revenue-dashboard", str(self.openai.calls[-1].context))


class StateAndRegistryTests(unittest.TestCase):
    def test_confirmed_onboarding_merges_without_erasing_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "projects" / "Example").mkdir(parents=True)
            path = save_context(root, project="Example", facts={"purpose": "first"}, confirmed=True)
            save_context(root, project="Example", facts={"priority": "second"}, confirmed=True)
            self.assertEqual(json.loads(path.read_text())["facts"], {"purpose": "first", "priority": "second"})
            with self.assertRaises(SkillStateError):
                save_context(root, project="Example", facts={"purpose": "guess"}, confirmed=False)
            with self.assertRaises(SkillStateError):
                save_context(root, project="Example", facts={"api_key": "private"}, confirmed=True)
            self.assertEqual(json.loads(path.read_text())["facts"]["purpose"], "first")

    def test_link_checks_paths_deduplicates_and_marks_urls_unverified(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            root = Path(folder)
            target = root / "source.txt"
            target.write_text("original")
            registry = SourceRegistry(root)
            item = registry.register(str(target), "reference")
            self.assertTrue(item["verified"])
            self.assertEqual(registry.register(str(target), "reference")["id"], item["id"])
            self.assertFalse(registry.register("https://example.org/data", "remote reference")["verified"])
            with self.assertRaises(SourceRegistryError):
                registry.register("https://example.org/other", "related", related_ids=("unknown",))
            with self.assertRaises(SourceRegistryError):
                registry.register("https://example.org/data?token=private", "unsafe url")
            with self.assertRaises(SourceRegistryError):
                registry.register(str(root / "missing.txt"), "missing")
            target.unlink()
            self.assertEqual(registry.validate(None)[0]["issue"], "stale_local_target")

    def test_optional_viewer_uses_only_selected_route_metadata_and_relationships(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            root = Path(folder)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_text("PRIVATE BODY MUST NOT APPEAR")
            second.write_text("ANOTHER PRIVATE BODY")
            registry = SourceRegistry(root)
            registry.register(str(first), "First route", source_id="first")
            registry.register(str(second), "Second route", source_id="second", related_ids=("first",))
            output = root / "viewer.html"
            completed = subprocess.run(
                ["python3", str(ROOT / "skills" / "3d-brain" / "scripts" / "build.py"), "--output", str(output), "--include", "first", "--include", "second"],
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            page = output.read_text()
            self.assertIn('"related_ids": ["first"]', page)
            self.assertNotIn("PRIVATE BODY MUST NOT APPEAR", page)

    def test_interview_pause_prevents_new_answers_until_resume(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"AIOS_DATA_DIR": folder}):
            store = SkillInterviewStore(Path(folder))
            session = store.start(None, "topic")
            store.set_status(None, session["id"], "paused")
            with self.assertRaises(SkillStateError):
                store.append(None, session["id"], "question", "answer")
            store.set_status(None, session["id"], "active")
            self.assertEqual(len(store.append(None, session["id"], "question", "answer")["answers"]), 1)


class AuditFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("config", "skills", ".agents", ".claude"):
            shutil.copytree(ROOT / name, self.root / name)
        (self.root / "projects" / "Example").mkdir(parents=True)
        self.state = self.root / "private-state"
        self.env = patch.dict(os.environ, {"AIOS_DATA_DIR": str(self.state), "AIOS_TRACE_FILE": str(self.root / "traces.jsonl")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.model = patch("py_dev.skill_audit.discover_gguf", return_value=self.root / "fake.gguf")
        self.model.start()
        self.addCleanup(self.model.stop)
        self.meta = patch("py_dev.skill_audit._read_gguf_metadata", return_value={"general.architecture": "qwen3", "qwen3.context_length": 40960, "general.file_type": 15})
        self.meta.start()
        self.addCleanup(self.meta.stop)
        self.live = patch("py_dev.skill_audit.inspect_local", return_value=fake_report())
        self.live.start()
        self.addCleanup(self.live.stop)

    def ids(self, **kwargs):
        return {item["id"] for item in audit(self.root, project="Example", live=True, **kwargs)["findings"]}

    def test_correct_architecture_has_no_confirmed_defects(self):
        report = audit(self.root, project="Example", live=True)
        self.assertFalse([item for item in report["findings"] if item["classification"] == "confirmed defect"])

    def test_invalid_inheritance_and_permission_bypass(self):
        (self.root / "projects" / "Example" / "aios.toml").write_text('inherits = ["none"]\n[tools]\nleast_privilege = false\n')
        self.assertIn("AUD-003", self.ids())

    def test_reasoning_profile_cannot_embed_tool_permissions(self):
        defaults = self.root / "config" / "defaults.toml"
        data = defaults.read_text().replace('[reasoning.profiles.xhigh]\nthinking = true\nbudget_tokens = 16384', '[reasoning.profiles.xhigh]\nthinking = true\nbudget_tokens = 16384\ntools = ["filesystem_write"]')
        defaults.write_text(data)
        self.assertIn("AUD-003", self.ids())

    def test_context_above_runtime_capacity_is_identified(self):
        defaults = self.root / "config" / "defaults.toml"
        data = defaults.read_text().replace('[task_profiles.skill_audit]\nreasoning = "high"\ncontext = "standard"', '[task_profiles.skill_audit]\nreasoning = "high"\ncontext = "large"')
        defaults.write_text(data)
        self.assertIn("AUD-007", self.ids())

    def test_external_escalation_violation_is_detected_from_run_evidence(self):
        (self.root / "traces.jsonl").write_text(json.dumps({"escalation_decision": "verification_failed_to_openai", "external_escalation_enabled": False}) + "\n")
        self.assertIn("AUD-008", self.ids())

    def test_missing_endpoint_is_a_verification_gap(self):
        with patch("py_dev.skill_audit.inspect_local", side_effect=LocalRuntimeError("endpoint down")):
            report = audit(self.root, project="Example", live=True)
        self.assertIn("AUD-006", {item["id"] for item in report["findings"]})

    def test_stale_link_hardcoded_model_and_contradictory_mirror(self):
        state = self.root / "projects" / "Example" / "state"
        state.mkdir()
        (state / "sources.json").write_text(json.dumps({"sources": [{"id": "missing", "mechanism": "local_path", "target": str(self.root / "gone")}] }))
        (self.root / "projects" / "Example" / "main.py").write_text('MODEL = "/Users/example/model.gguf"\n')
        mirror = self.root / ".agents" / "skills" / "audit" / "SKILL.md"
        mirror.write_text(mirror.read_text() + "\nContradictory instruction.\n")
        self.assertTrue({"AUD-002", "AUD-009", "AUD-010"} <= self.ids())


if __name__ == "__main__":
    unittest.main()
