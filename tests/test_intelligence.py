from __future__ import annotations

import unittest
from dataclasses import replace
from types import SimpleNamespace

from py_dev import IntelligenceRequest, IntelligenceService, ModelRouter, ModelSettings, ToolDefinition
from py_dev.models import ProviderResult, ToolCall, ModelRequest, ToolOutput
from py_dev.providers import ProviderUnavailable
from py_dev.providers.openai import OpenAIProvider
from py_dev.providers.claude import ClaudeProvider

EMPTY = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}


class SequenceProvider:
    def __init__(self, name, outcomes):
        self.name, self.model, self.outcomes, self.calls = name, name + "-test", list(outcomes), []

    def available(self):
        return True

    def generate(self, request):
        self.calls.append(request)
        result = self.outcomes.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def result(content="Completed successfully", calls=(), model="openai-test"):
    return ProviderResult(content, model, "tool_call" if calls else "completed", 1, {"input_tokens": 2}, tuple(calls), ())


class IntelligenceTests(unittest.TestCase):
    def harness(self, outcomes, *, qwen=(), claude=()):
        providers = {"openai": SequenceProvider("openai", outcomes), "qwen_local": SequenceProvider("qwen_local", qwen), "claude": SequenceProvider("claude", claude)}
        settings = ModelSettings(qwen_model="qwen_local-test", openai_model="openai-test", claude_model="claude-test", openai_enabled=True, claude_enabled=True, allow_cloud_escalation=True, cloud_call_budget=20)
        router = ModelRouter(settings, providers=providers, audit_sink=lambda event: None)
        events = []
        return IntelligenceService(router=router, event_sink=events.append), providers, events

    def request(self, **changes):
        return replace(IntelligenceRequest("Write expected records", "test-system", "run-1", provider="openai"), **changes)

    def test_false_success_rejected_without_fallback(self):
        import sqlite3
        service, providers, events = self.harness([result()])
        from contextlib import closing
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE TABLE records(id INTEGER PRIMARY KEY)")
            db.executemany("INSERT INTO records VALUES(?)", ((i,) for i in range(700)))
            db.commit()
            actual = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            out = service.run(self.request(verifier=lambda output, trace: db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 1000))
        self.assertEqual(actual, 700)
        self.assertEqual(out.status, "rejected")
        self.assertIs(out.verification_metadata["deterministic"], False)
        self.assertEqual(len(providers["openai"].calls), 1)
        self.assertFalse(providers["qwen_local"].calls)
        self.assertEqual(events[-1]["verification_status"], "failed")

    def test_unverified_text_remains_proposal(self):
        service, _, _ = self.harness([result()])
        self.assertEqual(service.run(self.request()).status, "proposed")

    def test_allowlisted_tool_returns_and_trace_omits_arguments(self):
        tool = ToolDefinition("read_count", "Read count", EMPTY, lambda args, key: {"count": 1000})
        service, providers, events = self.harness([result(calls=(ToolCall("call-1", "read_count", {}),)), result()])
        out = service.run(self.request(tools=(tool,), authorized_tools=frozenset({"read_count"}), verifier=lambda output, trace: len(trace) == 1))
        self.assertEqual(out.status, "verified")
        self.assertEqual(providers["openai"].calls[1].tool_outputs[0].output, {"count": 1000})
        self.assertEqual(events[-1]["tool_calls"][0]["name"], "read_count")
        self.assertNotIn("arguments", events[-1]["tool_calls"][0])

    def test_high_risk_mutation_requires_authorization(self):
        writes = []
        tool = ToolDefinition("write", "Write", EMPTY, lambda args, key: writes.append(key), mutating=True, risk="high", verifier=lambda a, r: True)
        service, _, _ = self.harness([result(calls=(ToolCall("c1", "write", {}),))])
        out = service.run(self.request(tools=(tool,), authorized_tools=frozenset({"write"})))
        self.assertEqual(out.status, "review")
        self.assertFalse(writes)

    def test_failed_write_never_falls_back_or_retries(self):
        writes = []
        def failed(args, key):
            writes.append(key)
            raise OSError("after commit")
        tool = ToolDefinition("write", "Write", EMPTY, failed, mutating=True, verifier=lambda a, r: True)
        service, providers, _ = self.harness([result(calls=(ToolCall("c1", "write", {}),))])
        out = service.run(self.request(tools=(tool,), authorized_tools=frozenset({"write"}), human_approved_tools=frozenset({"write"})))
        self.assertEqual(out.status, "uncertain")
        self.assertEqual(len(writes), 1)
        self.assertFalse(providers["qwen_local"].calls)

    def test_read_failure_after_committed_write_remains_uncertain(self):
        writes = []
        write = ToolDefinition("write", "Write", EMPTY, lambda args, key: writes.append(key), mutating=True, verifier=lambda a, r: True)
        def fail(args, key):
            raise OSError("read failed")
        read = ToolDefinition("read", "Read", EMPTY, fail)
        service, providers, _ = self.harness([result(calls=(ToolCall("c1", "write", {}), ToolCall("c2", "read", {})))])
        out = service.run(self.request(tools=(write, read), authorized_tools=frozenset({"write", "read"}), human_approved_tools=frozenset({"write"})))
        self.assertEqual(out.status, "uncertain")
        self.assertEqual(len(writes), 1)
        self.assertFalse(providers["qwen_local"].calls)

    def test_read_write_read_reobserves_actual_state(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("CREATE TABLE records(id INTEGER PRIMARY KEY)")
            db.executemany("INSERT INTO records VALUES(?)",((i,) for i in range(700)))
            reads=[]
            def read(args,key):
                count=db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                reads.append(count);return {"count":count}
            def write(args,key):
                db.executemany("INSERT INTO records VALUES(?)",((i,) for i in range(700,1000)))
                db.commit();return {"written":300}
            tools=(ToolDefinition("read","Count current records",EMPTY,read),
                   ToolDefinition("write","Complete records",EMPTY,write,mutating=True,verifier=lambda a,r:db.execute("SELECT COUNT(*) FROM records").fetchone()[0]==1000))
            service,providers,_=self.harness([result(calls=(ToolCall("c1","read",{}),ToolCall("c2","write",{}),ToolCall("c3","read",{}))),result()])
            output=service.run(self.request(tools=tools,authorized_tools=frozenset({"read","write"}),human_approved_tools=frozenset({"write"})))
            self.assertEqual(reads,[700,1000])
            self.assertEqual(providers["openai"].calls[1].tool_outputs[-1].output,{"count":1000})

    def test_unknown_capabilities_context_residency_and_model_pin_fail_closed(self):
        for change in ({"required_capabilities": frozenset({"mcp"})}, {"constraints": {"context_size": 200}}, {"constraints": {"residency": "eu"}}, {"constraints": {"model": "different"}}):
            service, providers, _ = self.harness([result()])
            self.assertIn(service.run(self.request(**change)).status, {"unavailable", "rejected"})
            self.assertFalse(providers["openai"].calls)

    def test_private_requests_never_route_cloud(self):
        service, providers, _ = self.harness([result()])
        self.assertEqual(service.run(self.request(privacy="private")).status, "unavailable")
        self.assertFalse(providers["openai"].calls)

    def test_per_run_cloud_limit_includes_fallback(self):
        service, providers, _ = self.harness([ProviderUnavailable("down")], qwen=[ProviderUnavailable("down")], claude=[result(model="claude-test")])
        out = service.run(self.request(constraints={"max_cloud_calls": 1}))
        self.assertEqual(out.status, "unavailable")
        self.assertFalse(providers["claude"].calls)
        self.assertEqual(service.router.remaining_cloud_calls, 19)

    def test_total_provider_attempt_bound_includes_fallback(self):
        service, providers, _ = self.harness([ProviderUnavailable("down")], qwen=[result(model="qwen_local-test")])
        out = service.run(self.request(max_provider_calls=1))
        self.assertEqual(out.status, "unavailable")
        self.assertFalse(providers["qwen_local"].calls)

    def test_explicit_review_cannot_reset_per_run_limits(self):
        for limits in ({"max_cloud_calls": 1}, {"max_provider_attempts": 1}):
            service, providers, _ = self.harness([result()], claude=[result(model="claude-test")])
            response=service.router.run(ModelRequest(({"role":"user","content":"answer"},),brain="openai",review_with="claude",**limits))
            self.assertEqual(len(providers["openai"].calls),1)
            self.assertFalse(providers["claude"].calls)
            self.assertTrue(response.review.degraded)

    def test_attempts_keep_request_run_and_caller_attribution(self):
        service,providers,_=self.harness([result()])
        events=[];service.router.audit_sink=events.append
        request=self.request()
        service.run(request)
        self.assertEqual((events[0].request_id,events[0].run_id,events[0].calling_system),
                         (request.request_id,request.run_id,request.calling_system))

    def test_schema_and_allowlist_checked_before_side_effect(self):
        writes = []
        tool = ToolDefinition("read", "Read", EMPTY, lambda a, k: writes.append(1))
        service, _, _ = self.harness([result(calls=(ToolCall("c1", "read", {"unexpected": 1}),))])
        self.assertEqual(service.run(self.request(tools=(tool,), authorized_tools=frozenset({"read"}))).status, "rejected")
        self.assertFalse(writes)

    def test_invalid_limits_and_empty_tools_fail_before_invocation(self):
        for change in ({"max_provider_calls": True}, {"constraints": {"max_cloud_calls": None}}, {"constraints": {"timeout_seconds": float("nan")}}, {"required_capabilities": frozenset({"tools"})}):
            service, providers, _ = self.harness([result()])
            self.assertEqual(service.run(self.request(**change)).status, "rejected")
            self.assertFalse(providers["openai"].calls)


class NativeToolTests(unittest.TestCase):
    def test_incomplete_openai_response_cannot_propose_execution(self):
        output=SimpleNamespace(output_text="",output=[SimpleNamespace(type="function_call",call_id="c1",name="read",arguments="{}")],model="m",status="incomplete",usage=None)
        client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs:output))
        adapter=OpenAIProvider("m",client)
        request=ModelRequest(({"role":"user","content":"read"},),tools=({"name":"read","parameters":EMPTY},),tool_requirement=True)
        with self.assertRaises(ProviderUnavailable):adapter.generate(request)

    def test_openai_native_calls_and_continuation(self):
        captured = []
        output = SimpleNamespace(output_text="", output=[SimpleNamespace(type="function_call", call_id="c1", name="read", arguments="{}")], model="m", status="completed", usage=None)
        client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (captured.append(kwargs), output)[1]))
        adapter = OpenAIProvider("m", client)
        request = ModelRequest(({"role": "user", "content": "read"},), tools=({"name": "read", "parameters": EMPTY},), tool_requirement=True)
        response = adapter.generate(request)
        self.assertEqual(response.tool_calls[0].name, "read")
        self.assertEqual(captured[0]["tools"][0]["type"], "function")
        adapter.generate(replace(request, provider_state=response.provider_state, tool_outputs=(ToolOutput("c1", "read", {"count": 3}),)))
        self.assertEqual(captured[1]["input"][-1]["type"], "function_call_output")
        self.assertFalse(captured[0]["store"])

    def test_claude_native_calls_and_continuation(self):
        captured = []
        output = SimpleNamespace(content=[SimpleNamespace(type="tool_use", id="c1", name="read", input={})], model="m", stop_reason="tool_use", usage=None)
        client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: (captured.append(kwargs), output)[1]))
        adapter = ClaudeProvider("m", client)
        request = ModelRequest(({"role": "user", "content": "read"},), tools=({"name": "read", "parameters": EMPTY},), tool_requirement=True)
        response = adapter.generate(request)
        self.assertEqual(response.tool_calls[0].name, "read")
        adapter.generate(replace(request, provider_state=response.provider_state, tool_outputs=(ToolOutput("c1", "read", 3),)))
        self.assertEqual(captured[1]["messages"][-1]["content"][0]["type"], "tool_result")


if __name__ == "__main__":
    unittest.main()
