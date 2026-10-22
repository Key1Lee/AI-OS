"""Bounded, process-local metadata only; no prompts, tokens, or record bodies."""
from collections import deque
from dataclasses import asdict
from threading import Lock
from time import perf_counter
from math import ceil


class Telemetry:
    def __init__(self):
        self.events = deque(maxlen=1000)
        self.lock = Lock()

    def record(self, **event):
        with self.lock:
            self.events.append(event)

    def summary(self):
        with self.lock:
            events = list(self.events)
        requests = [e for e in events if e["kind"] == "http"]
        latencies = sorted(e["latency_ms"] for e in requests)
        llm = [e for e in events if e["kind"] == "llm"]
        return {"window": "last 1000 events; resets on restart", "requests": len(requests),
                "errors": sum(e["status"] >= 500 and e["status"] != 501 for e in requests),
                "pending_exercises": sum(e["status"] == 501 for e in requests),
                "p95_latency_ms": latencies[ceil(len(latencies) * .95) - 1] if latencies else None,
                "tool_calls": sum(e["kind"] == "tool" for e in events),
                "provider_input_tokens": sum(e["input_tokens"] for e in llm if e["usage_kind"] == "provider_tokens"),
                "provider_output_tokens": sum(e["output_tokens"] for e in llm if e["usage_kind"] == "provider_tokens"),
                "fake_input_words": sum(e["input_tokens"] for e in llm if e["usage_kind"] == "estimated_words"),
                "fake_output_words": sum(e["output_tokens"] for e in llm if e["usage_kind"] == "estimated_words"),
                "events": events[-30:]}


class ObservedProvider:
    def __init__(self, provider, telemetry):
        self.provider, self.telemetry = provider, telemetry

    def complete(self, prompt, *, passages=None):
        start = perf_counter()
        try:
            completion = self.provider.complete(prompt, passages=passages)
        except Exception:
            self.telemetry.record(kind="llm_error", provider=self.provider.name, latency_ms=round((perf_counter()-start)*1000, 2))
            raise
        info = asdict(completion)
        info.pop("text")
        self.telemetry.record(kind="llm", provider=self.provider.name, latency_ms=round((perf_counter()-start)*1000, 2), **info)
        return completion
