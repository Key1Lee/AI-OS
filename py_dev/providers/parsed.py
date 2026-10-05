"""Central transport for migrated typed evaluators; no project/provider SDK coupling.

Projects retain Pydantic domain models and prompts. The shared router still owns
cloud gates, budgets, availability, fallback, audit and the actual client.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from time import monotonic
from datetime import datetime, timezone
import re
from typing import Any, Callable, Mapping
from urllib.request import urlopen

from ..config import ModelSettings
from ..models import ModelRequest, ModelResponse, ProviderResult
from ..router import ModelRouter
from ..telemetry import EventSink
from .base import ProviderUnavailable, usage_dict
from .openai import OpenAIProvider
from .qwen_local import QwenLocalProvider


def credential_configured(provider: str) -> bool:
    return bool(os.getenv({"openai": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY", "jev": "TYPESAFE_API_KEY"}.get(provider, ""), "").strip()) if provider != "qwen_local" else True


@dataclass(frozen=True)
class ParsedResult:
    output: Any
    response_id: str | None
    model: str
    usage: Mapping[str, Any]
    latency_ms: int


class ParsedModelClient:
    def __init__(self, provider: str, model: str, *, calling_system: str, base_url: str | None = None, timeout_seconds: float = 90, client: Any = None, settings: ModelSettings | None = None, event_sink=None):
        self.provider, self.model, self.calling_system = provider, model, calling_system
        self.timeout_seconds = timeout_seconds
        self.client = client  # Test injection seam; production creation is central.
        configured = settings or ModelSettings.from_env()
        self.settings = replace(configured, **({"openai_model": model} if provider == "openai" else {"qwen_model": model, "qwen_base_url": base_url or configured.qwen_base_url}))
        self.event_sink = event_sink or EventSink()
        self.response_id = None

    def health_check(self, timeout: float = 1.5) -> tuple[bool, str | None]:
        if self.provider != "qwen_local":
            return credential_configured(self.provider), None if credential_configured(self.provider) else "Provider credentials are not configured"
        if not self.settings.qwen_enabled:
            return False, "Qwen is disabled by central policy"
        try:
            if self.client is not None:
                ids = [str(item.id) for item in self.client.models.list(timeout=timeout).data]
            else:
                base = QwenLocalProvider(self.model, self.settings.qwen_base_url).base_url
                with urlopen(base + "/models", timeout=timeout) as response:
                    ids = [str(item["id"]) for item in json.load(response).get("data", [])]
            if not ids:
                return False, "Qwen endpoint returned no models"
            if self.model and self.model not in ids:
                return False, "Qwen endpoint is serving a different model"
            if not self.model:
                self.model = next((item for item in ids if "qwen" in item.casefold()), "")
                if not self.model:
                    return False, "Endpoint exposes no identifiable Qwen model; configure an explicit alias"
                self.settings = replace(self.settings, qwen_model=self.model)
            return True, None
        except Exception as exc:
            return False, f"Qwen health check failed: {type(exc).__name__}"

    def parse(self, *, output_type: Any, instructions: str, context: Mapping[str, Any], run_id: str, request_id: str, reasoning_effort: str | None = None, max_output_tokens: int = 1800, store: bool = False, previous_response_id: str | None = None) -> ParsedResult:
        label = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
        if any(not isinstance(value, str) or not label.fullmatch(value) for value in (self.calling_system, run_id, request_id)):
            raise ValueError("Parsed calls require safe attribution identifiers")
        owner = self

        def record_attempt(status, latency_ms, usage=None):
            owner.event_sink({"request_id": request_id, "calling_system": owner.calling_system, "run_id": run_id,
                              "capability": "structured_evaluation", "provider": owner.provider, "model": owner.model,
                              "latency_ms": latency_ms, "usage": usage or {}, "status": status,
                              "tool_calls": 0, "fallback": False, "verification_status": "invalid"})

        class ParsedAdapter:
            name = owner.provider
            model = owner.model

            def available(self):
                return owner.client is not None or (OpenAIProvider(owner.model).available() if owner.provider == "openai" else bool(owner.model))

            def generate(self, request: ModelRequest):
                started = monotonic()
                try:
                    if owner.provider == "openai":
                        if owner.client is None:
                            from openai import OpenAI
                            owner.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=owner.timeout_seconds, max_retries=0)
                        arguments = {"model": owner.model, "instructions": instructions, "input": json.dumps(context, ensure_ascii=False), "text_format": output_type, "max_output_tokens": max_output_tokens, "store": store}
                        if reasoning_effort:
                            arguments["reasoning"] = {"effort": reasoning_effort}
                        if previous_response_id:
                            arguments["previous_response_id"] = previous_response_id
                        try:
                            response = owner.client.responses.parse(**arguments)
                        except Exception as exc:
                            # Explicit conversation recovery consumes another central reservation.
                            if previous_response_id and getattr(exc, "status_code", None) in {400, 404}:
                                # Record the failed physical call before reserving a
                                # recovery call. Audit failure prevents continuation.
                                router._audit(request, router.route(request), owner.provider, "session_recovery_failed",
                                              "invalid", int((monotonic() - started) * 1000), False, datetime.now(timezone.utc).isoformat())
                                record_attempt("session_recovery_failed", int((monotonic() - started) * 1000))
                                if not router.budget.reserve():
                                    raise ProviderUnavailable("Conversation recovery budget exhausted")
                                arguments.pop("previous_response_id", None)
                                response = owner.client.responses.parse(**arguments)
                            else:
                                raise
                        parsed = getattr(response, "output_parsed", None)
                        if parsed is None:
                            raise ProviderUnavailable("Provider returned no valid structured decision")
                        parsed = output_type.model_validate(parsed)
                        owner.response_id = getattr(response, "id", None)
                        return ProviderResult(parsed.model_dump_json(), str(getattr(response, "model", None) or owner.model), "completed", int((monotonic() - started) * 1000), usage_dict(getattr(response, "usage", None)))
                    if owner.client is not None:
                        response = owner.client.chat.completions.create(model=owner.model, messages=[{"role": "system", "content": instructions}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}], response_format={"type": "json_object"}, temperature=0, max_tokens=max_output_tokens)
                        content = response.choices[0].message.content
                        owner.response_id = getattr(response, "id", None)
                        raw = ProviderResult(content, owner.model, "stop", int((monotonic() - started) * 1000))
                    else:
                        raw = QwenLocalProvider(owner.model, owner.settings.qwen_base_url).generate(request)
                    output_type.model_validate_json(raw.content)
                    return raw
                except ProviderUnavailable:
                    raise
                except Exception as exc:
                    raise ProviderUnavailable("Provider unavailable or invalid structured output") from exc

        router = ModelRouter(self.settings, providers={self.provider: ParsedAdapter()}, validator=lambda req, result: output_type.model_validate_json(result.content))
        request = ModelRequest(messages=({"role": "user", "content": json.dumps(context, ensure_ascii=False)},), system_instructions=instructions + "\nReturn JSON matching: " + json.dumps(output_type.model_json_schema()), task_id=request_id, workflow=self.calling_system, brain=self.provider, pinned_model=self.model, allowed_providers=frozenset({self.provider}), allow_fallback=False, privacy_requirement=self.provider == "qwen_local", timeout_seconds=self.timeout_seconds, max_output_tokens=max_output_tokens, metadata={"run_id": run_id})
        result: ModelResponse = router.run(request)
        self.event_sink({"request_id": request_id, "calling_system": self.calling_system, "run_id": run_id, "capability": "structured_evaluation", "provider": self.provider, "model": self.model, "latency_ms": result.latency_ms, "usage": dict(result.usage), "status": "unavailable" if result.degraded else "proposed", "tool_calls": 0, "fallback": False, "verification_status": result.validation_status})
        if result.degraded:
            raise ProviderUnavailable("Provider unavailable or invalid structured JSON/decision; central policy may deny the call")
        return ParsedResult(output_type.model_validate_json(result.content), self.response_id, result.model or self.model, result.usage, result.latency_ms or 0)


def select_evaluators(requested: str, llm_mode: str, *, qwen_factory: Callable[[], Any], openai_factory: Callable[[], Any], unavailable_type: type[Exception]):
    """Compatibility selection remains central; factories produce project rubric adapters."""
    if requested == "offline_fallback" or requested == "auto" and llm_mode == "off":
        return (), ("explicitly configured",)
    providers, failures = [], []
    if requested == "openai":
        try:
            providers.append(openai_factory())
        except unavailable_type as exc:
            failures.append(str(exc))
    if requested in {"auto", "qwen_local", "openai"}:
        qwen = qwen_factory()
        healthy, reason = qwen.health_check()
        if healthy:
            providers.append(qwen)
        else:
            failures.append(reason or "Qwen endpoint unhealthy")
    if not providers and llm_mode == "required":
        raise unavailable_type("; ".join(failures) or "Required evaluator unavailable")
    return tuple(providers), tuple(failures)


def invoke_evaluators(providers, invoke, unavailable_type):
    failures = []
    for provider in providers:
        try:
            return invoke(provider), "; ".join(failures) or None
        except unavailable_type as exc:
            failures.append(f"{provider.name}: {exc}")
    raise unavailable_type("; ".join(failures) or "No reasoning evaluator available")
