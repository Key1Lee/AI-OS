from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple[Mapping[str, str], ...]
    system_instructions: str = ""
    task_type: str = "general"
    context: Mapping[str, Any] = field(default_factory=dict)
    tool_permissions: frozenset[str] = frozenset()
    structured_output_schema: Mapping[str, Any] | None = None
    reasoning_level: str | None = None
    thinking_enabled: bool | None = None
    reasoning_budget_tokens: int | None = None
    max_output_tokens: int | None = None
    timeout_seconds: float = 90.0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    task_id: str = ""
    workflow: str = ""
    brain: str = "auto"
    review_with: str | None = None
    privacy_requirement: bool = False
    offline_requirement: bool = False
    coding_requirement: bool = False
    context_size: int = 0
    difficulty: str = "medium"
    latency_preference: str = "balanced"
    cost_preference: str = "low"
    tool_requirement: bool = False
    image_requirement: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    selected_provider: str | None
    selected_model: str | None
    mode: str
    reason: str
    fallback_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelResponse:
    content: str = ""
    structured_output: Any = None
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    usage: Mapping[str, Any] = field(default_factory=dict)
    finish_status: str = "unknown"
    validation_status: str = "not_requested"
    error: str | None = None
    routing: RoutingDecision | None = None
    effective_provider: str | None = None
    fallback_occurred: bool = False
    degraded: bool = False
    review: ModelResponse | None = None


@dataclass(frozen=True)
class ProviderResult:
    content: str
    model: str
    finish_status: str
    latency_ms: int
    usage: Mapping[str, Any] = field(default_factory=dict)
