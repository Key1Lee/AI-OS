from __future__ import annotations

import os
import shutil
import struct
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from py_dev import ModelSettings
from py_dev.context_policy import ContextLimitError, choose_context
from py_dev.local_runtime import LocalRuntimeError, LocalRuntimeReport, _read_gguf_metadata, discover_gguf, inspect_local
from py_dev.models import ProviderResult
from py_dev.providers import ProviderUnavailable
from py_dev.runtime import AIOSRuntime, RuntimeInput, SessionState
from py_dev.runtime_config import RuntimeConfigError, RuntimeConfigResolver


ROOT = Path(__file__).resolve().parents[1]


def write_fake_gguf(path: Path) -> None:
    entries = (("general.architecture", 8, "qwen3"), ("general.name", 8, "Qwen test"), ("qwen3.context_length", 4, 40960), ("general.file_type", 4, 15))
    with path.open("wb") as stream:
        stream.write(b"GGUF" + struct.pack("<IQQ", 3, 1, len(entries)))
        for key, kind, value in entries:
            raw_key = key.encode()
            stream.write(struct.pack("<Q", len(raw_key)) + raw_key + struct.pack("<I", kind))
            if kind == 8:
                raw_value = value.encode()
                stream.write(struct.pack("<Q", len(raw_value)) + raw_value)
            else:
                stream.write(struct.pack("<I", value))
        stream.write(b"\0" * 1024)


def fake_report(*, budget_verified: bool = False, runtime_context: int = 32768) -> LocalRuntimeReport:
    return LocalRuntimeReport(
        Path("/tmp/Qwen3-4B-Q4_K_M.gguf"), "Qwen3-4B-Q4_K_M.gguf", "Q4_K_M",
        "Qwen3-4B-Q4_K_M", {"n_ctx_train": 40960}, Path("/tmp/llama-server"),
        "version: test", ("MTL0: test",), "auto", 99, True,
        runtime_context, 40960, "http://127.0.0.1:8080/v1", True, False, True,
        budget_verified,
    )


class FakeProvider:
    def __init__(self, name: str, outcome: str | Exception = "ready"):
        self.name = name
        self.model = f"test-{name}"
        self.outcome = outcome
        self.calls = []

    def available(self):
        return True

    def generate(self, request):
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return ProviderResult(self.outcome, self.model, "stop", 7, {"prompt_tokens": 19, "completion_tokens": 2})


def runtime(*, report=None, settings=None, qwen=None, openai=None, resolver=None, validator=None, optional_verifier=None):
    traces, audits = [], []
    providers = {
        "qwen_local": qwen or FakeProvider("qwen_local"),
        "openai": openai or FakeProvider("openai"),
        "claude": FakeProvider("claude"),
    }
    instance = AIOSRuntime(
        resolver=resolver,
        base_settings=settings or ModelSettings(),
        local_probe=lambda config: report or fake_report(),
        providers=providers,
        audit_sink=audits.append,
        trace_sink=traces.append,
        validator=validator,
        optional_verifier=optional_verifier,
    )
    return instance, providers, traces, audits


class InheritanceTests(unittest.TestCase):
    def test_global_defaults_and_unconfigured_project_inherit(self):
        resolver = RuntimeConfigResolver()
        global_config = resolver.resolve()
        northstar = resolver.resolve(project="Northstar")
        for config in (global_config, northstar):
            self.assertEqual(config.get("runtime", "provider"), "qwen_local")
            self.assertEqual(config.get("reasoning", "default"), "medium")
            self.assertEqual(config.get("context", "default_tokens"), 32768)
            self.assertFalse(config.get("external_escalation", "enabled"))
        self.assertEqual(northstar.source("runtime", "provider"), "global")

    def test_provider_project_task_and_run_precedence(self):
        config = RuntimeConfigResolver().resolve(project="Toptal-Testing", task="system_design", run={"reasoning": "none", "max_output": 2048})
        self.assertEqual(config.layers, ("global", "provider:qwen_local", "project:Toptal-Testing", "task:system_design", "run"))
        self.assertEqual(config.get("runtime", "endpoint"), "http://127.0.0.1:8080/v1")
        self.assertEqual(config.source("runtime", "endpoint"), "provider:qwen_local")
        self.assertEqual(config.get("context", "tier"), "large")
        self.assertEqual(config.source("context", "tier"), "task:system_design")
        self.assertEqual(config.get("generation", "max_output_tokens"), 2048)
        self.assertEqual(config.source("generation", "max_output_tokens"), "run")
        self.assertEqual(config.get("reasoning", "default"), "none")

    def test_project_changes_only_its_preference(self):
        resolver = RuntimeConfigResolver()
        self.assertEqual(resolver.resolve(project="Toptal-Testing").get("generation", "max_output_tokens"), 4096)
        self.assertEqual(resolver.resolve(project="Northstar").get("generation", "max_output_tokens"), 8192)

    def test_all_reasoning_profiles_are_configuration_driven(self):
        config = RuntimeConfigResolver().resolve()
        expected = {"none": (False, 0), "low": (True, 1024), "medium": (True, 4096), "high": (True, 8192), "xhigh": (True, 16384)}
        for name, pair in expected.items():
            profile = config.get("reasoning", "profiles", name)
            self.assertEqual((profile["thinking"], profile["budget_tokens"]), pair)

    def test_invalid_configuration_and_project_path_are_rejected(self):
        resolver = RuntimeConfigResolver()
        with self.assertRaises(RuntimeConfigError):
            resolver.resolve(project="../Northstar")
        with self.assertRaises(RuntimeConfigError):
            resolver.resolve(run={"provider": "unknown"})
        with self.assertRaises(RuntimeConfigError):
            resolver.resolve(run={"context": "gigantic"})
        with self.assertRaises(RuntimeConfigError):
            resolver.resolve(run={"max_output": 0})

    def test_invalid_project_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copytree(ROOT / "config", root / "config")
            project = root / "projects" / "Example"
            project.mkdir(parents=True)
            (project / "aios.toml").write_text('inherits = ["none"]\n[project]\nname = "Example"\n', encoding="utf-8")
            with self.assertRaises(RuntimeConfigError):
                RuntimeConfigResolver(root).resolve(project="Example")


class ContextTests(unittest.TestCase):
    def test_dynamic_context_uses_smallest_sufficient_tier(self):
        config = RuntimeConfigResolver().resolve()
        plan = choose_context(config, fake_report(), prompt_text="short task", reasoning_budget=0, output_tokens=64)
        self.assertEqual((plan.tier, plan.limit_tokens), ("small", 16384))

    def test_large_task_cannot_exceed_running_server(self):
        config = RuntimeConfigResolver().resolve(project="Toptal-Testing", task="system_design")
        with self.assertRaises(ContextLimitError):
            choose_context(config, fake_report(), prompt_text="design", reasoning_budget=8192, output_tokens=2048)

    def test_context_overflow_is_rejected_without_truncation(self):
        config = RuntimeConfigResolver().resolve()
        with self.assertRaises(ContextLimitError):
            choose_context(config, fake_report(), prompt_text="x" * 120000, reasoning_budget=0, output_tokens=8192)


class StartupTests(unittest.TestCase):
    def test_quantization_and_native_context_come_from_gguf_header(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "misleading-Q8.gguf"
            write_fake_gguf(model)
            metadata = _read_gguf_metadata(model)
            self.assertEqual(metadata["general.file_type"], 15)
            self.assertEqual(metadata["qwen3.context_length"], 40960)

    def test_missing_model_is_actionable(self):
        config = RuntimeConfigResolver().resolve(run={"model_path": "/tmp/definitely-missing-qwen.gguf"})
        with self.assertRaisesRegex(LocalRuntimeError, "missing or too small"):
            discover_gguf(config)

    def test_unavailable_server_is_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "Qwen-test.gguf"
            write_fake_gguf(model)
            config = RuntimeConfigResolver().resolve(run={"model_path": str(model), "endpoint": "http://127.0.0.1:65535/v1"})
            with patch("py_dev.local_runtime.discover_binary", return_value=Path("/tmp/llama-server")), patch("py_dev.local_runtime._binary_info", return_value=("test", (), False)):
                with self.assertRaisesRegex(LocalRuntimeError, "unavailable"):
                    inspect_local(config)

    def test_wrong_loaded_model_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "Qwen-test.gguf"
            write_fake_gguf(model)
            config = RuntimeConfigResolver().resolve(run={"model_path": str(model), "model": "expected"})
            def fake_get(url, timeout=3):
                if url.endswith("/health"):
                    return {"status": "ok"}
                return {"data": [{"id": "wrong"}]}
            with patch("py_dev.local_runtime.discover_binary", return_value=Path("/tmp/llama-server")), patch("py_dev.local_runtime._binary_info", return_value=("test", (), False)), patch("py_dev.local_runtime._get_json", side_effect=fake_get):
                with self.assertRaisesRegex(LocalRuntimeError, "identity"):
                    inspect_local(config)


@patch.dict(os.environ, {}, clear=True)
class RuntimeTests(unittest.TestCase):
    def test_local_provider_selection_and_trace(self):
        instance, providers, traces, audits = runtime()
        result = instance.run(RuntimeInput(prompt="hello", project="Toptal-Testing", task="rapid_recall", task_id="run-1", overrides={"reasoning": "none", "max_output": 64}))
        self.assertEqual(result.response.provider, "qwen_local")
        self.assertEqual(result.context_plan.tier, "small")
        self.assertFalse(providers["openai"].calls)
        self.assertEqual(traces[0].project, "Toptal-Testing")
        self.assertEqual((traces[0].actual_prompt_tokens, traces[0].output_tokens), (19, 2))
        self.assertEqual(traces[0].reasoning_profile, "none")
        self.assertEqual(traces[0].verification_result, "basic_valid")
        self.assertEqual(audits[0].attempted_provider, "qwen_local")

    def test_per_run_provider_model_and_output_override(self):
        cloud = ModelSettings(openai_enabled=True, openai_model="old", cloud_call_budget=1)
        instance, providers, traces, _ = runtime(settings=cloud)
        result = instance.run(RuntimeInput(prompt="hello", overrides={"provider": "openai", "model": "new-model", "max_output": 128}))
        self.assertEqual(result.response.provider, "openai")
        self.assertEqual(providers["openai"].calls[0].max_output_tokens, 128)
        self.assertEqual(traces[0].escalation_decision, "manual_cloud")
        self.assertFalse(providers["qwen_local"].calls)

    def test_reasoning_profiles_map_into_qwen_request_when_verified(self):
        instance, providers, _, _ = runtime(report=fake_report(budget_verified=True))
        for name, budget in (("none", 0), ("low", 1024), ("medium", 4096), ("high", 8192), ("xhigh", 16384)):
            result = instance.run(RuntimeInput(prompt="hello", overrides={"reasoning": name, "max_output": 64}))
            call = providers["qwen_local"].calls[-1]
            self.assertEqual(call.reasoning_budget_tokens, budget)
            self.assertEqual(call.thinking_enabled, name != "none")
            self.assertTrue(result.trace.reasoning_budget_enforced)

    def test_unverified_budget_falls_back_to_thinking_mode(self):
        instance, providers, traces, _ = runtime(report=fake_report(budget_verified=False))
        instance.run(RuntimeInput(prompt="hello", overrides={"reasoning": "high", "max_output": 64}))
        self.assertIsNone(providers["qwen_local"].calls[0].reasoning_budget_tokens)
        self.assertTrue(providers["qwen_local"].calls[0].thinking_enabled)
        self.assertEqual(traces[0].reasoning_method, "thinking_toggle")

    def test_escalation_disabled_blocks_paid_fallback(self):
        base = ModelSettings(openai_enabled=True, openai_model="cloud", cloud_call_budget=2, allow_cloud_escalation=True)
        instance, providers, _, _ = runtime(settings=base, qwen=FakeProvider("qwen_local", ProviderUnavailable("down")))
        result = instance.run(RuntimeInput(prompt="hello"))
        self.assertTrue(result.response.degraded)
        self.assertFalse(providers["openai"].calls)

    def test_reasoning_does_not_grant_tools(self):
        instance, providers, _, _ = runtime()
        with self.assertRaisesRegex(RuntimeConfigError, "authorization"):
            instance.run(RuntimeInput(prompt="hello", overrides={"reasoning": "xhigh", "tools": ["filesystem_write"]}))
        self.assertFalse(providers["qwen_local"].calls)

    def test_disabling_optional_verification_does_not_disable_hard_validator(self):
        def reject(request, response):
            raise ValueError("hard rule failed")
        instance, providers, traces, _ = runtime(validator=reject)
        result = instance.run(RuntimeInput(prompt="hello", overrides={"verification": False, "max_output": 64}))
        self.assertTrue(result.response.degraded)
        self.assertEqual(traces[0].verification_result, "failed")
        self.assertFalse(providers["openai"].calls)

    def test_optional_verification_failure_escalates_only_when_enabled(self):
        resolver = RuntimeConfigResolver()
        resolver.global_defaults["external_escalation"]["enabled"] = True
        base = ModelSettings(openai_enabled=True, openai_model="cloud", cloud_call_budget=1, allow_cloud_escalation=True)
        instance, providers, traces, _ = runtime(
            resolver=resolver, settings=base,
            qwen=FakeProvider("qwen_local", "bad"), openai=FakeProvider("openai", "good"),
            optional_verifier=lambda run, response: response.content == "good",
        )
        result = instance.run(RuntimeInput(prompt="hello", overrides={"max_output": 64}))
        self.assertEqual(result.response.provider, "openai")
        self.assertEqual(traces[0].verification_result, "passed_after_escalation")
        self.assertEqual(len(providers["openai"].calls), 1)

    def test_session_and_project_state_stay_separate_from_trace(self):
        instance, providers, traces, _ = runtime()
        instance.run(RuntimeInput(prompt="hello", session=SessionState(({"role": "user", "content": "prior session"},)), project_state={"decision": "private project fact"}, overrides={"max_output": 64}))
        call = providers["qwen_local"].calls[0]
        self.assertEqual(call.messages[0]["content"], "prior session")
        self.assertEqual(call.context["critical_project_state"]["decision"], "private project fact")
        self.assertNotIn("private project fact", repr(traces[0]))


if __name__ == "__main__":
    unittest.main()
