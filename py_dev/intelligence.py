"""A bounded capability facade over ModelRouter; workflows retain tools and truth."""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass, field, replace
from time import monotonic
from typing import Any, Callable, Mapping

from .config import ModelSettings
from .models import ModelRequest, ToolOutput
from .router import ModelRouter
from .telemetry import EventSink
from .validation import parse_structured, validate_schema

_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_CAPABILITIES = {"reasoning", "planning", "coding", "structured_output", "tools"}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Mapping[str, Any]
    # Workflows implement idempotency durably for mutations; key is supplied here.
    handler: Callable[[Mapping[str, Any], str], Any]
    mutating: bool = False
    risk: str = "low"
    verifier: Callable[[Mapping[str, Any], Any], bool] | None = None


@dataclass(frozen=True)
class IntelligenceRequest:
    task: str
    calling_system: str
    run_id: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Mapping[str, Any] = field(default_factory=dict)
    required_capabilities: frozenset[str] = frozenset({"reasoning"})
    constraints: Mapping[str, Any] = field(default_factory=dict)
    privacy: str = "public"
    latency_class: str = "balanced"
    cost_class: str = "low"
    tools: tuple[ToolDefinition, ...] = ()
    structured_output_schema: Mapping[str, Any] | None = None
    system_instructions: str = ""
    provider: str = "auto"
    max_provider_calls: int = 4
    max_tool_calls: int = 8
    authorized_tools: frozenset[str] = frozenset()
    human_approved_tools: frozenset[str] = frozenset()
    # Trusted workflow checks real state. An LLM never supplies this callback.
    verifier: Callable[[Any, tuple[Mapping[str, Any], ...]], bool] | None = None


@dataclass(frozen=True)
class IntelligenceResult:
    request_id: str
    provider: str | None = None
    model: str | None = None
    output: Any = None
    tool_trace: tuple[Mapping[str, Any], ...] = ()
    usage: Mapping[str, int] = field(default_factory=dict)
    latency_ms: int = 0
    status: str = "unavailable"
    verification_metadata: Mapping[str, Any] = field(default_factory=dict)
    fallback: bool = False
    error: str | None = None


class IntelligenceService:
    def __init__(self, settings: ModelSettings | None = None, *, router: ModelRouter | None = None, event_sink: Callable[[Mapping[str, Any]], None] | None = None):
        self.router = router or ModelRouter(settings or ModelSettings.from_env())
        self.event_sink = event_sink or EventSink()

    def run(self, request: IntelligenceRequest) -> IntelligenceResult:
        started = monotonic()
        trace: list[Mapping[str, Any]] = []
        usage: dict[str, int] = {}
        provider = model = None
        fallback = False

        def finish(status: str, output: Any = None, error: str | None = None, verified: bool | None = None):
            result = IntelligenceResult(request.request_id, provider, model, output, tuple(trace), usage, int((monotonic() - started) * 1000), status, {"deterministic": verified, "claim_is_proof": False}, fallback, error)
            try:
                identifiers = {name: value if isinstance(value, str) and _LABEL.fullmatch(value) else "unlabeled" for name, value in (("request_id", request.request_id), ("calling_system", request.calling_system), ("run_id", request.run_id))}
                self.event_sink({**identifiers, "capability": sorted(request.required_capabilities & _CAPABILITIES), "provider": provider, "model": model, "latency_ms": result.latency_ms, "usage": usage, "status": status, "tool_calls": [dict(item) for item in trace], "fallback": fallback, "verification_status": "passed" if verified else "failed" if verified is False else "not_requested"})
            except Exception:
                return replace(result, status="uncertain" if any(item.get("mutating") for item in trace) else "unavailable", error="Intelligence telemetry could not be recorded")
            return result

        if any(not isinstance(value, str) or not _LABEL.fullmatch(value) for value in (request.request_id, request.calling_system, request.run_id)):
            return finish("rejected", error="Attribution requires safe nonempty identifiers")
        if not request.task or request.required_capabilities - _CAPABILITIES:
            return finish("rejected", error="Unsupported or unknown capability")
        if request.privacy not in {"public", "private", "local_only"} or request.cost_class not in {"free", "local", "low", "balanced", "high"} or request.latency_class not in {"fast", "balanced", "batch"}:
            return finish("rejected", error="Unknown privacy, cost or latency policy")
        allowed_constraints = {"model", "allowed_providers", "local_only", "offline", "residency", "context_size", "timeout_seconds", "max_output_tokens", "allow_fallback", "max_cloud_calls", "high_cost_approved"}
        if set(request.constraints) - allowed_constraints:
            return finish("rejected", error="Unknown constraint")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (request.max_provider_calls, request.max_tool_calls)) or request.max_provider_calls < 1 or request.max_provider_calls > 16 or request.max_tool_calls < 0 or request.max_tool_calls > 32:
            return finish("rejected", error="Run bounds exceed policy")
        for name in ("local_only", "offline", "allow_fallback", "high_cost_approved"):
            if name in request.constraints and not isinstance(request.constraints[name], bool):
                return finish("rejected", error="Boolean constraint has invalid type")
        for name in ("context_size", "max_cloud_calls", "max_output_tokens"):
            value = request.constraints.get(name)
            if name in request.constraints and (isinstance(value, bool) or not isinstance(value, int) or value < (1 if name == "max_output_tokens" else 0)):
                return finish("rejected", error="Numeric constraint has invalid type or range")
        timeout = request.constraints.get("timeout_seconds", 90)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            return finish("rejected", error="Timeout exceeds policy")
        if "tools" in request.required_capabilities and not request.tools:
            return finish("rejected", error="Tool capability requires a workflow-owned allowlist")
        if "structured_output" in request.required_capabilities and request.structured_output_schema is None:
            return finish("rejected", error="Structured capability requires a schema")
        if request.cost_class == "high" and request.constraints.get("high_cost_approved") is not True:
            return finish("review", error="High-cost request requires explicit approval")
        definitions = {tool.name: tool for tool in request.tools}
        if len(definitions) != len(request.tools) or any(not _LABEL.fullmatch(name) for name in definitions):
            return finish("rejected", error="Invalid or duplicate tool allowlist")
        try:
            for tool in request.tools:
                validate_schema(tool.parameters)
                if tool.risk not in {"low", "medium", "high", "critical"}:
                    raise ValueError("Unknown tool risk")
            if request.structured_output_schema:
                validate_schema(request.structured_output_schema)
        except ValueError:
            return finish("rejected", error="Invalid tool or output contract")
        constraints = request.constraints
        wire = ModelRequest(messages=({"role": "user", "content": request.task},), system_instructions=request.system_instructions, context=request.context, task_id=request.request_id, workflow=request.calling_system, task_type="coding" if "coding" in request.required_capabilities else "general", brain=request.provider, privacy_requirement=request.privacy != "public" or constraints.get("local_only", False), offline_requirement=constraints.get("offline", False), coding_requirement="coding" in request.required_capabilities, cost_preference=request.cost_class, latency_preference=request.latency_class, context_size=constraints.get("context_size", 0), timeout_seconds=constraints.get("timeout_seconds", 90), max_output_tokens=constraints.get("max_output_tokens"), structured_output_schema=request.structured_output_schema, tool_requirement=bool(request.tools) or "tools" in request.required_capabilities, tools=tuple({"name": tool.name, "description": tool.description, "parameters": tool.parameters} for tool in request.tools), pinned_model=constraints.get("model"), allowed_providers=frozenset(constraints.get("allowed_providers", ())), residency=constraints.get("residency", "any"), allow_fallback=constraints.get("allow_fallback", True), max_cloud_calls=constraints.get("max_cloud_calls"))
        wire = replace(wire, metadata={"run_id": request.run_id})
        executed: dict[str, Any] = {}
        cloud_before = self.router.remaining_cloud_calls
        cloud_limit = constraints.get("max_cloud_calls", request.max_provider_calls)
        attempts_remaining = request.max_provider_calls
        for step in range(request.max_provider_calls):
            if attempts_remaining <= 0:
                return finish("uncertain" if trace else "unavailable", error="Provider call limit reached")
            wire = replace(wire, max_provider_attempts=attempts_remaining, max_cloud_calls=max(0, cloud_limit - (cloud_before - self.router.remaining_cloud_calls)), metadata={"run_id": request.run_id})
            if cloud_before - self.router.remaining_cloud_calls >= cloud_limit:
                wire = replace(wire, max_cloud_calls=0)
            # After any mutation, fail independently: no alternate provider may replay work.
            wrote = any(item.get("mutating") for item in trace)
            if wrote:
                wire = replace(wire, allow_fallback=False)
            response = self.router.run(wire)
            attempts_remaining -= response.provider_attempts
            provider = response.effective_provider or response.provider
            model = response.model
            fallback = fallback or response.fallback_occurred
            for key, count in response.usage.items():
                if isinstance(count, int):
                    usage[key] = usage.get(key, 0) + count
            if response.degraded:
                return finish("uncertain" if wrote else "unavailable", error=response.error)
            if wire.pinned_model and response.model != wire.pinned_model:
                return finish("uncertain" if wrote else "rejected", error="Actual provider model violates the required model")
            if not response.tool_calls:
                output = response.structured_output if request.structured_output_schema is not None else response.content
                if request.verifier:
                    try:
                        passed = request.verifier(output, tuple(trace)) is True
                    except Exception:
                        passed = False
                    return finish("verified" if passed else "rejected", output, None if passed else "Deterministic workflow verification rejected the claimed result", passed)
                return finish("proposed", output)
            if step + 1 >= request.max_provider_calls:
                return finish("uncertain" if wrote else "rejected", error="Provider step limit reached before completion")
            if len(trace) + len(response.tool_calls) > request.max_tool_calls:
                return finish("uncertain" if wrote else "rejected", error="Tool call limit reached")
            outputs = []
            # Validate the complete batch before invoking any handler.
            for call in response.tool_calls:
                tool = definitions.get(call.name)
                if not isinstance(call.call_id, str) or not _LABEL.fullmatch(call.call_id):
                    return finish("uncertain" if wrote else "rejected", error="Invalid tool call identifier")
                if tool is None or call.name not in request.authorized_tools:
                    return finish("uncertain" if wrote else "rejected", error="Tool request is outside workflow authority")
                if (tool.mutating or tool.risk in {"high", "critical"}) and call.name not in request.human_approved_tools:
                    return finish("uncertain" if wrote else "review", error="Tool requires explicit human authorization")
                if tool.mutating and tool.verifier is None:
                    return finish("rejected", error="Mutating tool requires an observable-state verifier")
                try:
                    parse_structured(json.dumps(call.arguments, allow_nan=False), tool.parameters)
                except (ValueError, TypeError):
                    return finish("uncertain" if wrote else "rejected", error="Tool arguments violate the workflow contract")
            for call in response.tool_calls:
                tool = definitions[call.name]
                digest = hashlib.sha256(json.dumps({"name": call.name, "arguments": call.arguments}, sort_keys=True, allow_nan=False).encode()).hexdigest()
                key = request.request_id + ":" + digest
                record = {"call_id": call.call_id, "name": call.name, "mutating": tool.mutating, "risk": tool.risk, "idempotency_key": key, "status": "started"}
                trace.append(record)
                try:
                    if tool.mutating and key in executed:
                        result = executed[key]
                        record["status"] = "reused"
                    else:
                        result = tool.handler(call.arguments, key)
                        json.dumps(result, allow_nan=False)
                        if tool.mutating:
                            executed[key] = result
                        record["status"] = "verified" if tool.verifier else "returned"
                    if tool.verifier and tool.verifier(call.arguments, result) is not True:
                        record["status"] = "verification_failed"
                        return finish("uncertain" if any(item.get("mutating") for item in trace) else "rejected", error="Tool state verification failed", verified=False)
                    outputs.append(ToolOutput(call.call_id, call.name, result))
                except Exception:
                    record["status"] = "failed"
                    return finish("uncertain" if any(item.get("mutating") for item in trace) else "unavailable", error="Tool execution failed; workflow must reconcile observed state")
            wire = replace(wire, brain=provider, provider_state=response.provider_state, tool_outputs=tuple(outputs), allow_fallback=False)
        return finish("uncertain" if trace else "unavailable", error="Provider step limit reached")
