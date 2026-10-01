from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Callable, Mapping

from .capabilities import ModelCapabilities, registry
from .budget import CloudCallBudget
from .config import ModelSettings
from .models import ModelRequest, ModelResponse, RoutingDecision
from .providers import ClaudeProvider, ModelProvider, OpenAIProvider, ProviderUnavailable, QwenLocalProvider
from .validation import parse_structured, validate_schema


_NAMES = {"qwen": "qwen_local", "qwen_local": "qwen_local", "openai": "openai", "claude": "claude", "auto": "auto"}
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class AuditEvent:
    task_id: str
    workflow: str
    selected_provider: str | None
    attempted_provider: str
    selected_model: str
    routing_mode: str
    routing_reason: str
    fallback_occurrence: bool
    runtime: str | None
    quantization: str | None
    request_timestamp: str
    response_status: str
    latency_ms: int | None
    validation_status: str


class AuditUnavailable(RuntimeError):
    pass


class ModelRouter:
    """Policy-owned routing and invocation; adapters have no filesystem or tool authority."""

    def __init__(
        self,
        settings: ModelSettings,
        *,
        providers: Mapping[str, ModelProvider] | None = None,
        audit_sink: Callable[[AuditEvent], None] | None = None,
        validator: Callable[[ModelRequest, ModelResponse], None] | None = None,
    ) -> None:
        self.settings = settings
        self.capabilities = registry(settings)
        self.providers = dict(providers) if providers is not None else {
            "qwen_local": QwenLocalProvider(settings.qwen_model, settings.qwen_base_url),
            "openai": OpenAIProvider(settings.openai_model),
            "claude": ClaudeProvider(settings.claude_model),
        }
        self.budget = CloudCallBudget(settings.cloud_call_budget, settings.cloud_budget_file)
        self.audit_sink = audit_sink or self._default_audit
        self.validator = validator

    def _default_audit(self, event: AuditEvent) -> None:
        if self.settings.audit_file is None:
            logging.getLogger("py_dev.model_audit").info("%s", event)
            return
        path = self.settings.audit_file
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(json.dumps(asdict(event), separators=(",", ":")) + "\n")

    @staticmethod
    def _name(value: str) -> str:
        try:
            return _NAMES[value.strip().lower()]
        except (KeyError, AttributeError) as exc:
            raise ValueError("Brain must be auto, qwen, openai, or claude") from exc

    @property
    def remaining_cloud_calls(self) -> int:
        return self.budget.remaining

    def _allowed(self, name: str, request: ModelRequest, *, automatic_cloud: bool) -> bool:
        capability = self.capabilities[name]
        enabled = {"qwen_local": self.settings.qwen_enabled, "openai": self.settings.openai_enabled, "claude": self.settings.claude_enabled}[name]
        if not enabled or not capability.model or name not in self.providers:
            return False
        if not capability.local:
            if request.privacy_requirement or request.offline_requirement or self.remaining_cloud_calls <= 0:
                return False
            if automatic_cloud and not self.settings.allow_cloud_escalation:
                return False
        if request.tool_requirement and not capability.supports_tools:
            return False
        if request.image_requirement and not capability.supports_images:
            return False
        if request.structured_output_schema is not None and not capability.supports_structured_output:
            return False
        if request.context_size and capability.context_window and request.context_size > capability.context_window:
            return False
        return True

    def route(self, request: ModelRequest) -> RoutingDecision:
        if request.structured_output_schema is not None:
            validate_schema(request.structured_output_schema)
        requested = self._name(request.brain)
        mode = "manual" if requested != "auto" else "auto"
        if mode == "manual":
            preferred, reason = requested, "explicit task selection"
        elif request.workflow in self.settings.policy.workflow_overrides:
            preferred = self._name(self.settings.policy.workflow_overrides[request.workflow])
            reason = "workflow policy override"
        elif request.offline_requirement or request.privacy_requirement:
            preferred, reason = "qwen_local", "offline or private task"
        elif request.coding_requirement:
            preferred, reason = "openai", "coding requirement policy"
        elif request.task_type in self.settings.policy.task_preferences:
            preferred = self._name(self.settings.policy.task_preferences[request.task_type])
            reason = "task type policy"
        else:
            preferred = self._name(self.settings.default_brain)
            reason = "default local-first policy"
        if preferred == "auto":
            raise ValueError("Default brain and policy targets must name a provider")
        if mode == "manual" and not self._allowed(preferred, request, automatic_cloud=False):
            return RoutingDecision(None, None, mode, f"explicit {preferred} selection violates configuration or capability constraints")
        if mode == "auto" and not self._allowed(preferred, request, automatic_cloud=True):
            preferred = "qwen_local"
            reason += "; cloud or capability preference unavailable, using local policy"
        if not self._allowed(preferred, request, automatic_cloud=mode == "auto"):
            return RoutingDecision(None, None, mode, "no permitted reasoning provider")
        fallback = tuple(name for name in dict.fromkeys(self.settings.policy.fallback_order.get(preferred, ())) if name != preferred and self._allowed(name, request, automatic_cloud=True))
        return RoutingDecision(preferred, self.capabilities[preferred].model, mode, reason, fallback)

    def _audit(self, request: ModelRequest, decision: RoutingDecision, name: str, status: str, validation: str, latency: int | None, fallback: bool, request_timestamp: str) -> None:
        capability: ModelCapabilities = self.capabilities[name]
        event = AuditEvent(
            task_id=request.task_id if _SAFE_LABEL.fullmatch(request.task_id) else "unlabeled",
            workflow=request.workflow if _SAFE_LABEL.fullmatch(request.workflow) else "unlabeled",
            selected_provider=decision.selected_provider,
            attempted_provider=name,
            selected_model=capability.model,
            routing_mode=decision.mode,
            routing_reason=decision.reason,
            fallback_occurrence=fallback,
            runtime=capability.runtime,
            quantization=capability.quantization,
            request_timestamp=request_timestamp,
            response_status=status,
            latency_ms=latency,
            validation_status=validation,
        )
        try:
            self.audit_sink(event)
        except Exception as exc:
            raise AuditUnavailable("Model audit could not be recorded") from exc

    def _run_primary(self, request: ModelRequest, *, allow_fallback: bool) -> ModelResponse:
        decision = self.route(request)
        if decision.selected_provider is None:
            return ModelResponse(error=decision.reason, finish_status="degraded", validation_status="unavailable", routing=decision, degraded=True)
        candidates = (decision.selected_provider, *(decision.fallback_order if allow_fallback else ()))
        failures = []
        for index, name in enumerate(candidates):
            provider = self.providers[name]
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                available = provider.available()
            except Exception:
                available = False
            if not available:
                failures.append(f"{name} unavailable")
                self._audit(request, decision, name, "unavailable", "unavailable", None, index > 0, timestamp)
                continue
            if name != "qwen_local":
                if self.remaining_cloud_calls <= 0:
                    failures.append(f"{name} budget exhausted")
                    self._audit(request, decision, name, "budget_exhausted", "unavailable", None, index > 0, timestamp)
                    continue
                if not self.budget.reserve():
                    failures.append(f"{name} budget exhausted")
                    self._audit(request, decision, name, "budget_exhausted", "unavailable", None, index > 0, timestamp)
                    continue
            try:
                result = provider.generate(request)
                if result.finish_status not in {"stop", "completed", "end_turn", "stop_sequence"}:
                    raise ValueError("Model response was incomplete")
                parsed = parse_structured(result.content, request.structured_output_schema) if request.structured_output_schema is not None else None
                response = ModelResponse(
                    content=result.content,
                    structured_output=parsed,
                    provider=name,
                    model=result.model,
                    latency_ms=result.latency_ms,
                    usage=result.usage,
                    finish_status=result.finish_status,
                    validation_status="valid" if request.structured_output_schema is not None else "not_requested",
                    routing=decision,
                    effective_provider=name,
                    fallback_occurred=index > 0,
                )
                if self.validator:
                    try:
                        self.validator(request, response)
                    except Exception:
                        self._audit(request, decision, name, "rejected", "invalid", result.latency_ms, index > 0, timestamp)
                        return ModelResponse(error="Deterministic workflow validation rejected the response", finish_status="degraded", validation_status="invalid", routing=decision, degraded=True, effective_provider=name, fallback_occurred=index > 0)
                    response = replace(response, validation_status="valid")
                self._audit(request, decision, name, "success", response.validation_status, result.latency_ms, index > 0, timestamp)
                return response
            except (ProviderUnavailable, ValueError, TypeError, KeyError):
                failures.append(f"{name} failed validation or availability")
                self._audit(request, decision, name, "failed", "invalid", None, index > 0, timestamp)
            except AuditUnavailable:
                raise
            except Exception:
                failures.append(f"{name} failed availability")
                self._audit(request, decision, name, "failed", "invalid", None, index > 0, timestamp)
        return ModelResponse(error="; ".join(failures), finish_status="degraded", validation_status="unavailable", routing=decision, degraded=True, fallback_occurred=len(candidates) > 1)

    def run(self, request: ModelRequest) -> ModelResponse:
        try:
            return self._run_with_review(request)
        except AuditUnavailable as exc:
            return ModelResponse(error=str(exc), finish_status="degraded", validation_status="unavailable", degraded=True)

    def _run_with_review(self, request: ModelRequest) -> ModelResponse:
        primary = self._run_primary(request, allow_fallback=True)
        if not request.review_with or primary.degraded:
            return primary
        reviewer = self._name(request.review_with)
        if reviewer == "auto":
            raise ValueError("review_with must name a provider")
        review_request = replace(
            request,
            messages=(*request.messages, {"role": "assistant", "content": primary.content}, {"role": "user", "content": "Review the preceding response for omissions, contradictions, and errors. Give an independent assessment."}),
            task_type="second_opinion",
            brain=reviewer,
            review_with=None,
            structured_output_schema=None,
        )
        review = self._run_primary(review_request, allow_fallback=False)
        return replace(primary, review=review)
