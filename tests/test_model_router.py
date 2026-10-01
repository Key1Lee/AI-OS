from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from py_dev import ModelRequest, ModelRouter, ModelSettings, RoutingPolicy
from py_dev.models import ProviderResult
from py_dev.providers import ProviderUnavailable
from py_dev.providers.claude import ClaudeProvider
from py_dev.providers.openai import OpenAIProvider
from py_dev.providers.qwen_local import QwenLocalProvider


SCHEMA = {"type": "object", "properties": {"answer": {"type": "integer", "minimum": 0}}, "required": ["answer"], "additionalProperties": False}


class FakeProvider:
    def __init__(self, name: str, outcome: str | Exception = "ok", *, available: bool = True):
        self.name = name
        self.model = f"test-{name}"
        self.outcome = outcome
        self.ready = available
        self.calls = []

    def available(self) -> bool:
        return self.ready

    def generate(self, request: ModelRequest) -> ProviderResult:
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return ProviderResult(self.outcome, self.model, "stop", 12, {"input_tokens": 2})


def settings(**changes) -> ModelSettings:
    return replace(ModelSettings(qwen_model="local-test", openai_model="cloud-test-a", claude_model="cloud-test-b", openai_enabled=True, claude_enabled=True, cloud_call_budget=3, allow_cloud_escalation=True), **changes)


def harness(config: ModelSettings | None = None, *, qwen: FakeProvider | None = None, openai: FakeProvider | None = None, claude: FakeProvider | None = None, validator=None):
    events = []
    providers = {
        "qwen_local": qwen or FakeProvider("qwen_local"),
        "openai": openai or FakeProvider("openai"),
        "claude": claude or FakeProvider("claude"),
    }
    return ModelRouter(config or settings(), providers=providers, audit_sink=events.append, validator=validator), providers, events


def request(**changes) -> ModelRequest:
    return replace(ModelRequest(messages=({"role": "user", "content": "test"},), task_id="task-1", workflow="general"), **changes)


class RouterTests(unittest.TestCase):
    def test_qwen_is_default_and_explicit_qwen(self):
        router, _, _ = harness()
        self.assertEqual(router.route(request()).selected_provider, "qwen_local")
        self.assertEqual(router.route(request(brain="qwen")).selected_provider, "qwen_local")
        self.assertEqual(router.route(request(brain="qwen")).mode, "manual")

    def test_explicit_openai_and_claude(self):
        router, _, _ = harness()
        self.assertEqual(router.route(request(brain="openai")).selected_provider, "openai")
        self.assertEqual(router.route(request(brain="claude")).selected_provider, "claude")

    def test_auto_task_routing_and_coding_requirement(self):
        router, _, _ = harness()
        self.assertEqual(router.route(request(task_type="coding")).selected_provider, "openai")
        self.assertEqual(router.route(request(task_type="architecture_critique")).selected_provider, "claude")
        self.assertEqual(router.route(request(coding_requirement=True)).selected_provider, "openai")

    def test_policy_can_change_tasks_and_workflow_without_global_default(self):
        policy = RoutingPolicy(task_preferences={"coding": "claude"}, workflow_overrides={"my-workflow": "openai"})
        router, _, _ = harness(settings(policy=policy))
        self.assertEqual(router.route(request(task_type="coding")).selected_provider, "claude")
        self.assertEqual(router.route(request(workflow="my-workflow")).selected_provider, "openai")
        self.assertEqual(router.route(request(brain="qwen", workflow="my-workflow")).selected_provider, "qwen_local")

    def test_private_and_offline_never_use_cloud(self):
        for constraint in ({"privacy_requirement": True}, {"offline_requirement": True}):
            router, _, _ = harness()
            self.assertEqual(router.route(request(task_type="coding", **constraint)).selected_provider, "qwen_local")
            self.assertIsNone(router.route(request(brain="openai", **constraint)).selected_provider)
            self.assertEqual(router.route(request(**constraint)).fallback_order, ())

    def test_auto_cloud_escalation_requires_permission_and_budget(self):
        for config in (settings(allow_cloud_escalation=False), settings(cloud_call_budget=0), settings(openai_enabled=False)):
            router, _, _ = harness(config)
            self.assertEqual(router.route(request(task_type="coding")).selected_provider, "qwen_local")
        router, _, _ = harness(settings(allow_cloud_escalation=False))
        self.assertEqual(router.route(request(brain="openai")).selected_provider, "openai")

    def test_cloud_budget_persists_across_router_instances(self):
        with tempfile.TemporaryDirectory() as folder:
            config = settings(cloud_call_budget=1, cloud_budget_file=Path(folder) / "budget.json")
            first, _, _ = harness(config)
            self.assertEqual(first.run(request(brain="openai")).provider, "openai")
            second, _, _ = harness(config)
            self.assertIsNone(second.route(request(brain="openai")).selected_provider)
            self.assertEqual(json.loads(config.cloud_budget_file.read_text())["used"], 1)

    def test_disabled_manual_cloud_selection_is_rejected(self):
        router, providers, _ = harness(settings(openai_enabled=False))
        result = router.run(request(brain="openai"))
        self.assertTrue(result.degraded)
        self.assertFalse(providers["qwen_local"].calls)

    def test_qwen_outage_uses_permitted_fallback_and_reports_it(self):
        router, providers, events = harness(qwen=FakeProvider("qwen_local", ProviderUnavailable("offline")))
        result = router.run(request())
        self.assertEqual(result.provider, "openai")
        self.assertTrue(result.fallback_occurred)
        self.assertEqual(result.routing.selected_provider, "qwen_local")
        self.assertEqual([event.attempted_provider for event in events], ["qwen_local", "openai"])
        self.assertTrue(events[-1].fallback_occurrence)

    def test_qwen_outage_does_not_trigger_unapproved_cloud_call(self):
        router, providers, _ = harness(settings(allow_cloud_escalation=False), qwen=FakeProvider("qwen_local", ProviderUnavailable("offline")))
        result = router.run(request())
        self.assertTrue(result.degraded)
        self.assertFalse(providers["openai"].calls)

    def test_openai_and_claude_outages_are_safe(self):
        for brain in ("openai", "claude"):
            router, _, _ = harness(openai=FakeProvider("openai", ProviderUnavailable("down")), claude=FakeProvider("claude", ProviderUnavailable("down")))
            result = router.run(request(brain=brain))
            self.assertEqual(result.provider, "qwen_local")
            self.assertTrue(result.fallback_occurred)

    def test_all_outages_return_degraded_without_crash(self):
        router, _, _ = harness(qwen=FakeProvider("qwen_local", ProviderUnavailable("down")), openai=FakeProvider("openai", ProviderUnavailable("down")), claude=FakeProvider("claude", ProviderUnavailable("down")))
        result = router.run(request())
        self.assertTrue(result.degraded)
        self.assertEqual(result.finish_status, "degraded")

    def test_audit_failure_stops_fallback(self):
        providers = {name: FakeProvider(name) for name in ("qwen_local", "openai", "claude")}
        def broken_audit(event):
            raise OSError("disk full")
        router = ModelRouter(settings(), providers=providers, audit_sink=broken_audit)
        result = router.run(request())
        self.assertTrue(result.degraded)
        self.assertEqual(len(providers["qwen_local"].calls), 1)
        self.assertFalse(providers["openai"].calls)

    def test_metadata_is_recorded_without_request_contents(self):
        router, _, events = harness()
        router.run(request(metadata={"secret": "never-log-me"}, task_id="task-1", workflow="general"))
        event = events[0]
        self.assertEqual((event.task_id, event.workflow, event.attempted_provider), ("task-1", "general", "qwen_local"))
        self.assertEqual((event.runtime, event.quantization), ("llama.cpp", "Q4_K_S"))
        self.assertEqual((event.response_status, event.validation_status, event.latency_ms), ("success", "not_requested", 12))
        self.assertNotIn("never-log-me", repr(event))

    def test_default_audit_file_records_only_safe_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            config = settings(audit_file=Path(folder) / "audit.jsonl")
            providers = {name: FakeProvider(name) for name in ("qwen_local", "openai", "claude")}
            router = ModelRouter(config, providers=providers)
            router.run(request(metadata={"secret": "never-log-me"}))
            content = config.audit_file.read_text(encoding="utf-8")
            self.assertEqual(json.loads(content)["attempted_provider"], "qwen_local")
            self.assertNotIn("never-log-me", content)

    def test_structured_output_and_deterministic_validation(self):
        router, _, _ = harness(qwen=FakeProvider("qwen_local", '{"answer": 3}'), validator=lambda req, response: None if response.structured_output["answer"] == 3 else 1 / 0)
        result = router.run(request(structured_output_schema=SCHEMA))
        self.assertEqual(result.structured_output, {"answer": 3})
        self.assertEqual(result.validation_status, "valid")

    def test_hard_validation_rejection_cannot_be_overridden_by_fallback(self):
        def reject(req, response):
            raise ValueError("authorization failed")
        router, providers, _ = harness(qwen=FakeProvider("qwen_local", '{"answer": 3}'), validator=reject)
        result = router.run(request(structured_output_schema=SCHEMA))
        self.assertTrue(result.degraded)
        self.assertEqual(result.validation_status, "invalid")
        self.assertFalse(providers["openai"].calls)

    def test_invalid_structured_output_can_fallback(self):
        router, _, _ = harness(qwen=FakeProvider("qwen_local", '{"answer": "wrong"}'), openai=FakeProvider("openai", '{"answer": 5}'))
        result = router.run(request(structured_output_schema=SCHEMA))
        self.assertEqual((result.provider, result.structured_output), ("openai", {"answer": 5}))

    def test_duplicate_structured_fields_are_rejected(self):
        router, _, _ = harness(qwen=FakeProvider("qwen_local", '{"answer": 1, "answer": 2}'), openai=FakeProvider("openai", '{"answer": 5}'))
        result = router.run(request(structured_output_schema=SCHEMA))
        self.assertEqual(result.provider, "openai")

    def test_unsupported_schema_fails_closed(self):
        router, _, _ = harness()
        with self.assertRaises(ValueError):
            router.route(request(structured_output_schema={"type": "object", "oneOf": []}))

    def test_explicit_review_is_optional_and_budgeted(self):
        router, providers, _ = harness()
        plain = router.run(request())
        self.assertIsNone(plain.review)
        reviewed = router.run(request(review_with="claude"))
        self.assertEqual(reviewed.review.provider, "claude")
        self.assertEqual(len(providers["claude"].calls), 1)
        self.assertEqual(len(providers["openai"].calls), 0)
        self.assertEqual(router.remaining_cloud_calls, 2)

    def test_review_failure_keeps_valid_primary(self):
        router, _, _ = harness(claude=FakeProvider("claude", ProviderUnavailable("down")))
        result = router.run(request(review_with="claude"))
        self.assertFalse(result.degraded)
        self.assertTrue(result.review.degraded)

    def test_policy_file_is_configurable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "policy.json"
            path.write_text(json.dumps({"workflow_overrides": {"audit": "claude"}}), encoding="utf-8")
            router, _, _ = harness(settings(policy=RoutingPolicy.from_file(path)))
            self.assertEqual(router.route(request(workflow="audit")).selected_provider, "claude")

    def test_no_provider_can_execute_tools_or_images_until_supported(self):
        router, _, _ = harness()
        self.assertIsNone(router.route(request(tool_requirement=True)).selected_provider)
        self.assertIsNone(router.route(request(image_requirement=True)).selected_provider)


class AdapterTests(unittest.TestCase):
    def test_qwen_endpoint_must_be_loopback(self):
        for url in ("https://example.com/v1", "http://127.0.0.1.evil.com/v1", "http://user@localhost/v1"):
            with self.assertRaises(ValueError):
                QwenLocalProvider("model", url)
        self.assertEqual(QwenLocalProvider("model", "http://localhost:8080").base_url, "http://localhost:8080/v1")

    def test_openai_adapter_uses_configured_model_without_store(self):
        class Responses:
            def create(self, **kwargs):
                self.arguments = kwargs
                return type("Result", (), {"output_text": "ok", "model": "configured", "status": "completed", "usage": None})()
        client = type("Client", (), {"responses": Responses()})()
        result = OpenAIProvider("configured", client).generate(request())
        self.assertEqual(result.model, "configured")
        self.assertFalse(client.responses.arguments["store"])
        self.assertEqual(client.responses.arguments["model"], "configured")

    def test_claude_adapter_uses_configured_model(self):
        class Messages:
            def create(self, **kwargs):
                self.arguments = kwargs
                part = type("Part", (), {"type": "text", "text": "ok"})()
                return type("Result", (), {"content": [part], "model": "configured", "stop_reason": "end_turn", "usage": None})()
        client = type("Client", (), {"messages": Messages()})()
        result = ClaudeProvider("configured", client).generate(request())
        self.assertEqual(result.model, "configured")
        self.assertEqual(client.messages.arguments["model"], "configured")


if __name__ == "__main__":
    unittest.main()
