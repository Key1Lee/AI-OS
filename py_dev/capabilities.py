from __future__ import annotations

from dataclasses import dataclass

from .config import ModelSettings
from .local_runtime import LocalRuntimeReport


@dataclass(frozen=True)
class ModelCapabilities:
    provider: str
    model: str
    local: bool
    supports_tools: bool
    supports_structured_output: bool
    supports_reasoning_control: bool
    context_window: int | None
    supports_images: bool
    supports_code_workflows: bool
    cost_class: str
    privacy_class: str
    runtime: str | None = None
    quantization: str | None = None


def registry(settings: ModelSettings) -> dict[str, ModelCapabilities]:
    """Conservative adapter capabilities. Context windows remain unknown until configured."""
    return {
        "qwen_local": ModelCapabilities("qwen_local", settings.qwen_model, True, False, True, False, None, False, True, "local", "local", "llama.cpp", settings.qwen_quantization),
        "openai": ModelCapabilities("openai", settings.openai_model, False, False, True, True, None, False, True, "cloud", "cloud"),
        "claude": ModelCapabilities("claude", settings.claude_model, False, False, True, False, None, False, True, "cloud", "cloud"),
    }


def skill_capability_matrix(settings: ModelSettings, local_report: LocalRuntimeReport | None = None) -> dict[str, dict[str, object]]:
    """Expose configured Skill-routing facts without granting any tool authority."""
    capabilities = registry(settings)
    eligible = {
        "qwen_local": settings.qwen_enabled and local_report is not None,
        "openai": settings.openai_enabled and bool(settings.openai_model) and settings.cloud_call_budget > 0,
        "claude": settings.claude_enabled and bool(settings.claude_model) and settings.cloud_call_budget > 0,
    }
    return {
        name: {
            "eligible": eligible[name],
            "availability_verified": bool(local_report) if name == "qwen_local" else False,
            "local": capability.local,
            "cost_class": capability.cost_class,
            "context_limit": min(local_report.model_context, local_report.runtime_context) if name == "qwen_local" and local_report else capability.context_window,
            "thinking_control": bool(local_report and local_report.thinking_toggle) if name == "qwen_local" else capability.supports_reasoning_control,
            "repository_engineering": capability.supports_code_workflows,
            "tool_authority": False,
        }
        for name, capability in capabilities.items()
    }
