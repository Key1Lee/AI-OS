"""Readiness evidence is not inferred from SDK or credential presence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import os
from typing import Any, Mapping

from .config import ModelSettings
from .decision_config import DecisionSettings


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    supported: bool = True
    configured: bool = False
    credential_present: bool | None = None
    sdk_present: bool = True
    authenticated: bool | None = None
    tested: bool = False
    available: bool = False
    status: str = "SUPPORTED"
    model: str | None = None
    detail: str = "Live checks not performed"


def provider_health(*, settings: ModelSettings | None = None, decision_settings: DecisionSettings | None = None,
                    probe: bool = False) -> Mapping[str, Mapping[str, Any]]:
    """Probe cloud metadata and a bounded local task; never spends paid inference.

    Cloud metadata can prove authentication. AVAILABLE additionally requires a
    successful model-task check, intentionally not claimed by this metadata CLI.
    """
    settings = settings or ModelSettings.from_env()
    decision_settings = decision_settings or DecisionSettings.from_env()
    health = {}
    from .runtime import AIOSRuntime
    from .local_runtime import discover_gguf, _read_gguf_metadata, discover_binary
    try:
        overrides = {"provider": "qwen_local", "endpoint": settings.qwen_base_url}
        if settings.qwen_model:
            overrides["model"] = settings.qwen_model
        config = AIOSRuntime(base_settings=settings).resolve(overrides=overrides)
        path = discover_gguf(config)
        metadata = _read_gguf_metadata(path)
        discover_binary()
        local_configured = settings.qwen_enabled and metadata.get("general.architecture") == "qwen3"
        local_model = settings.qwen_model or path.stem
        detail = "Qwen GGUF and llama.cpp found; server/model-task untested"
    except Exception:
        local_configured = bool(settings.qwen_enabled and settings.qwen_model)
        local_model = settings.qwen_model or None
        detail = "Local runtime artifacts unavailable or configuration incomplete"
    local = ProviderHealth("qwen_local", configured=local_configured, credential_present=None,
                           status="CONFIGURED" if local_configured else "SUPPORTED", model=local_model, detail=detail)
    if probe and local_configured:
        try:
            from .local_runtime import inspect_local
            report = inspect_local(config, probe_budget=True)
            # Some runtimes lack a reasoning-budget probe. Verify actual task
            # completion separately before claiming TESTED or AVAILABLE.
            from .models import ModelRequest
            from .providers.qwen_local import QwenLocalProvider
            from .validation import parse_structured
            schema = {"type": "object", "properties": {"ready": {"type": "boolean"}},
                      "required": ["ready"], "additionalProperties": False}
            result = QwenLocalProvider(report.model_alias, settings.qwen_base_url).generate(ModelRequest(
                messages=({"role": "user", "content": 'Return {"ready":true}.'},),
                structured_output_schema=schema, max_output_tokens=32, timeout_seconds=5, thinking_enabled=False))
            if result.model != report.model_alias or result.finish_status not in {"stop", "completed"} or parse_structured(result.content, schema) != {"ready": True}:
                raise ValueError("Local model task check failed")
            local = ProviderHealth("qwen_local", configured=True, tested=True, available=True,
                                   status="AVAILABLE", model=report.model_alias, detail="Live local runtime and capability checks passed")
        except Exception:
            local = ProviderHealth("qwen_local", configured=True, status="UNAVAILABLE", model=local_model,
                                   detail="Local live runtime checks failed; no operational claim")
    health["qwen_local"] = asdict(local)
    specs = (("openai", settings.openai_enabled, settings.openai_model, "OPENAI_API_KEY", "openai"),
             ("claude", settings.claude_enabled, settings.claude_model, "ANTHROPIC_API_KEY", "anthropic"),
             ("jev", decision_settings.enabled, decision_settings.model, "TYPESAFE_API_KEY", "typesafe_sdk"))
    for name, enabled, model, key, sdk in specs:
        credential = bool(os.getenv(key, "").strip())
        sdk_present = importlib.util.find_spec(sdk) is not None
        configured = bool(enabled and model)
        status = "CONFIGURED" if configured else "SUPPORTED"
        authenticated = None
        detail = "Model task untested; credential presence is not authentication"
        if probe and configured:
            if not credential or not sdk_present:
                status, detail = "UNAVAILABLE", "Credential or optional SDK missing"
            else:
                client = None
                try:
                    if name == "openai":
                        from openai import OpenAI
                        client = OpenAI(timeout=5, max_retries=0)
                        client.models.retrieve(model)
                    elif name == "claude":
                        from anthropic import Anthropic
                        client = Anthropic(timeout=5, max_retries=0)
                        client.models.retrieve(model)
                    else:
                        from typesafe_sdk import TypeSafeClient, RetryPolicy
                        client = TypeSafeClient(timeout=5, retry=RetryPolicy(max_retries=0))
                        models = client.models.list().models
                        if model not in {item.name for item in models}:
                            raise ValueError("Configured model absent")
                    authenticated, status = True, "AUTHENTICATED"
                    detail = "Authenticated model metadata check passed; inference task remains untested"
                except Exception:
                    status, detail = "UNAVAILABLE", "Model metadata check failed; authentication unproved"
                finally:
                    if client is not None:
                        client.close()
        health[name] = asdict(ProviderHealth(name, configured=configured, credential_present=credential,
                                           sdk_present=sdk_present, authenticated=authenticated, status=status,
                                           model=model or None, detail=detail))
    return health
