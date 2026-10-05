"""AI-OS run boundary: inherited policy, local checks, model call, and trace."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .config import ModelSettings
from .context_policy import ContextPlan, choose_context
from .context_policy import ContextLimitError
from .local_runtime import LocalRuntimeError, LocalRuntimeReport, inspect_local
from .models import ModelRequest, ModelResponse
from .router import ModelRouter
from .runtime_config import ResolvedConfig, RuntimeConfigError, RuntimeConfigResolver


@dataclass(frozen=True)
class SessionState:
    """Temporary conversation context; never a durable project record."""

    messages: tuple[Mapping[str, str], ...] = ()


@dataclass(frozen=True)
class RuntimeInput:
    prompt: str
    project: str | None = None
    task: str | None = None
    task_id: str = ""
    system_instructions: str = ""
    session: SessionState = field(default_factory=SessionState)
    project_state: Mapping[str, Any] = field(default_factory=dict)
    retrieved_context: tuple[str, ...] = ()
    overrides: Mapping[str, Any] = field(default_factory=dict)
    authorized_tools: frozenset[str] = frozenset()
    task_type: str = "general"
    workflow: str = ""
    review_with: str | None = None
    private: bool = False
    offline: bool = False


@dataclass(frozen=True)
class RunTrace:
    timestamp: str
    project: str
    task_profile: str
    provider: str | None
    model: str | None
    context_limit: int | None
    estimated_prompt_tokens: int | None
    actual_prompt_tokens: int | None
    output_tokens: int | None
    reasoning_profile: str
    reasoning_budget_configured: int
    reasoning_budget_enforced: bool
    reasoning_method: str
    thinking_enabled: bool | None
    tool_calls: int
    verification_result: str
    latency_ms: int | None
    escalation_decision: str
    error: str | None
    external_escalation_enabled: bool | None = None


@dataclass(frozen=True)
class RuntimeResult:
    config: ResolvedConfig
    response: ModelResponse
    context_plan: ContextPlan | None
    local_runtime: LocalRuntimeReport | None
    trace: RunTrace


class AIOSRuntime:
    def __init__(
        self,
        resolver: RuntimeConfigResolver | None = None,
        *,
        base_settings: ModelSettings | None = None,
        local_probe: Callable[[ResolvedConfig], LocalRuntimeReport] | None = None,
        providers: Mapping[str, Any] | None = None,
        audit_sink: Callable[[Any], None] | None = None,
        trace_sink: Callable[[RunTrace], None] | None = None,
        validator: Callable[[ModelRequest, ModelResponse], None] | None = None,
        optional_verifier: Callable[[RuntimeInput, ModelResponse], bool] | None = None,
    ) -> None:
        self.resolver = resolver or RuntimeConfigResolver()
        self.base_settings = base_settings or ModelSettings.from_env()
        self.local_probe = local_probe or (lambda config: inspect_local(config, probe_budget=True))
        self.providers = providers
        self.audit_sink = audit_sink
        self.trace_sink = trace_sink or self._write_trace
        self.validator = validator
        self.optional_verifier = optional_verifier
        self._local_cache: dict[tuple[str, str], LocalRuntimeReport] = {}

    @staticmethod
    def _write_trace(trace: RunTrace) -> None:
        path = Path(os.getenv("AIOS_TRACE_FILE", str(Path.home() / ".config" / "py-dev" / "run-traces.jsonl"))).expanduser()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(json.dumps(asdict(trace), separators=(",", ":")) + "\n")

    def resolve(self, *, project: str | None = None, task: str | None = None, overrides: Mapping[str, Any] | None = None) -> ResolvedConfig:
        environment: dict[str, Any] = {}
        if os.getenv("DEFAULT_BRAIN"):
            environment["provider"] = "qwen_local" if os.environ["DEFAULT_BRAIN"] == "qwen" else os.environ["DEFAULT_BRAIN"]
        preliminary = self.resolver.resolve(project=project, task=task, run={**environment, **(overrides or {})})
        if preliminary.get("runtime", "provider") == "qwen_local":
            for name, key in (("QWEN_MODEL", "model"), ("QWEN_BASE_URL", "endpoint"), ("AIOS_QWEN_GGUF_PATH", "model_path")):
                if os.getenv(name):
                    environment[key] = os.environ[name]
            if os.getenv("AIOS_GPU_LAYERS"):
                raw = os.environ["AIOS_GPU_LAYERS"]
                try:
                    environment["gpu_layers"] = raw if raw == "auto" else int(raw)
                except ValueError as exc:
                    raise RuntimeConfigError("AIOS_GPU_LAYERS must be auto or a nonnegative integer") from exc
        return self.resolver.resolve(project=project, task=task, run={**environment, **(overrides or {})})

    def check_local(self, config: ResolvedConfig) -> LocalRuntimeReport:
        key = tuple(str(config.values["runtime"].get(name, "")) for name in ("model_path", "endpoint", "model", "gpu_layers"))
        if key not in self._local_cache:
            self._local_cache[key] = self.local_probe(config)
        return self._local_cache[key]

    def run(self, run: RuntimeInput) -> RuntimeResult:
        try:
            return self._run_inner(run)
        except (RuntimeConfigError, LocalRuntimeError, ContextLimitError, ValueError) as exc:
            safe = lambda value: value if value and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value) else "unlabeled"
            failure = RunTrace(
                timestamp=datetime.now(timezone.utc).isoformat(),
                project=safe(run.project), task_profile=safe(run.task),
                provider=None, model=None, context_limit=None,
                estimated_prompt_tokens=None, actual_prompt_tokens=None,
                output_tokens=None, reasoning_profile="unresolved",
                reasoning_budget_configured=0, reasoning_budget_enforced=False,
                reasoning_method="unresolved", thinking_enabled=None,
                tool_calls=0, verification_result="not_run", latency_ms=None,
                escalation_decision="none", error=type(exc).__name__,
            )
            try:
                self.trace_sink(failure)
            except Exception:
                pass
            raise

    def _run_inner(self, run: RuntimeInput) -> RuntimeResult:
        if not run.prompt.strip():
            raise RuntimeConfigError("Run prompt must not be empty")
        config = self.resolve(project=run.project, task=run.task, overrides=run.overrides)
        requested_tools = frozenset(config.get("tools", "requested"))
        if requested_tools - run.authorized_tools:
            raise RuntimeConfigError("Requested tools exceed workflow authorization")
        if requested_tools:
            raise RuntimeConfigError("Tool execution is not implemented in the shared runtime")
        provider = config.get("runtime", "provider")
        reasoning_name = config.get("reasoning", "default")
        reasoning = config.get("reasoning", "profiles", reasoning_name)
        output_tokens = config.get("generation", "max_output_tokens")
        if run.overrides.get("reasoning") and not config.get("reasoning", "allow_task_override"):
            raise RuntimeConfigError("Reasoning override is disabled by policy")
        report = self.check_local(config) if provider == "qwen_local" else None
        if report is not None and not report.thinking_toggle and reasoning_name == "none":
            raise RuntimeConfigError("The active Qwen template cannot disable thinking")
        context_payload: dict[str, Any] = {}
        if run.project_state:
            context_payload["critical_project_state"] = run.project_state
        if run.retrieved_context:
            context_payload["relevant_retrieved_context"] = list(run.retrieved_context)
        messages = (*run.session.messages, {"role": "user", "content": run.prompt})
        prompt_text = run.system_instructions + run.prompt + json.dumps(context_payload, ensure_ascii=False) + "".join(str(item.get("content", "")) for item in run.session.messages)
        effective_budget = reasoning["budget_tokens"] if report and report.budget_verified else 0
        plan = choose_context(config, report, prompt_text=prompt_text, reasoning_budget=effective_budget, output_tokens=output_tokens) if report else None
        configured_model = config.values["runtime"].get("model")
        settings = replace(
            self.base_settings,
            default_brain=provider,
            qwen_model=report.model_alias if report else self.base_settings.qwen_model,
            qwen_base_url=report.endpoint if report else self.base_settings.qwen_base_url,
            qwen_quantization=report.quantization if report else self.base_settings.qwen_quantization,
            openai_model=(configured_model or self.base_settings.openai_model) if provider == "openai" else self.base_settings.openai_model,
            claude_model=(configured_model or self.base_settings.claude_model) if provider == "claude" else self.base_settings.claude_model,
            allow_cloud_escalation=self.base_settings.allow_cloud_escalation and config.get("external_escalation", "enabled"),
        )
        model_request = ModelRequest(
            messages=messages,
            system_instructions=run.system_instructions,
            task_type=run.task or run.task_type,
            context=context_payload,
            task_id=run.task_id,
            workflow=run.workflow or run.project or "global",
            brain=provider,
            review_with=run.review_with,
            max_output_tokens=output_tokens,
            context_size=plan.limit_tokens if plan else 0,
            thinking_enabled=reasoning["thinking"] if report and report.thinking_toggle else None,
            reasoning_budget_tokens=reasoning["budget_tokens"] if report and report.budget_verified else None,
            tool_permissions=frozenset(),
            privacy_requirement=run.private,
            offline_requirement=run.offline or (provider == "qwen_local" and not config.get("external_escalation", "enabled") and not run.review_with),
        )
        router = ModelRouter(settings, providers=self.providers, audit_sink=self.audit_sink, validator=self.validator)
        if report:
            router.capabilities["qwen_local"] = replace(router.capabilities["qwen_local"], context_window=min(report.model_context, report.runtime_context))
        response = router.run(model_request)
        verification_result = "failed" if response.degraded else "not_requested"
        escalation_decision = "fallback" if response.fallback_occurred else "manual_cloud" if provider != "qwen_local" else "none"
        if not response.degraded and config.get("verification", "enabled"):
            if self.optional_verifier is None:
                verification_result = "workflow_valid" if self.validator else "basic_valid"
            else:
                try:
                    verified = bool(self.optional_verifier(run, response))
                except Exception:
                    verified = False
                if not verified and provider == "qwen_local" and config.get("external_escalation", "enabled") and not (run.private or run.offline):
                    for candidate, enabled in (("openai", settings.openai_enabled), ("claude", settings.claude_enabled)):
                        if not enabled:
                            continue
                        # Local startup proves a local ceiling only. Cloud limits remain
                        # unknown; an explicit context guarantee cannot be inferred.
                        escalated = router.run(replace(model_request, brain=candidate, review_with=None, context_size=0))
                        escalation_decision = f"verification_failed_to_{candidate}"
                        if escalated.degraded:
                            continue
                        try:
                            verified = bool(self.optional_verifier(run, escalated))
                        except Exception:
                            verified = False
                        if verified:
                            response = escalated
                            break
                if verified:
                    verification_result = "passed_after_escalation" if escalation_decision.startswith("verification_failed_to_") else "passed"
                else:
                    verification_result = "failed"
                    response = replace(response, degraded=True, error="Optional verification rejected the response", validation_status="invalid", finish_status="degraded")
        usage = response.usage
        trace = RunTrace(
            timestamp=datetime.now(timezone.utc).isoformat(),
            project=run.project or "global",
            task_profile=run.task or "general",
            provider=response.effective_provider,
            model=response.model,
            context_limit=plan.limit_tokens if plan else None,
            estimated_prompt_tokens=plan.estimated_prompt_tokens if plan else None,
            actual_prompt_tokens=usage.get("prompt_tokens", usage.get("input_tokens")),
            output_tokens=usage.get("completion_tokens", usage.get("output_tokens")),
            reasoning_profile=reasoning_name,
            reasoning_budget_configured=reasoning["budget_tokens"],
            reasoning_budget_enforced=bool(report and report.budget_verified),
            reasoning_method="budget" if report and report.budget_verified else ("thinking_toggle" if report and report.thinking_toggle else "provider_default"),
            thinking_enabled=model_request.thinking_enabled,
            tool_calls=0,
            verification_result=verification_result,
            latency_ms=response.latency_ms,
            escalation_decision=escalation_decision,
            error=response.error,
            external_escalation_enabled=config.get("external_escalation", "enabled"),
        )
        if config.get("tracing", "enabled"):
            try:
                self.trace_sink(trace)
            except Exception as exc:
                raise RuntimeConfigError("Run trace could not be recorded") from exc
        return RuntimeResult(config, response, plan, report, trace)
