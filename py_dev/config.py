from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


DEFAULT_TASK_PREFERENCES = {
    "implementation": "openai",
    "coding": "openai",
    "debugging": "openai",
    "code_review": "openai",
    "sql": "openai",
    "architecture_critique": "claude",
    "requirements_review": "claude",
    "document_analysis": "claude",
    "second_opinion": "claude",
}


@dataclass(frozen=True)
class RoutingPolicy:
    task_preferences: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_TASK_PREFERENCES))
    workflow_overrides: Mapping[str, str] = field(default_factory=dict)
    fallback_order: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: {
        "qwen_local": ("openai", "claude"),
        "openai": ("qwen_local", "claude"),
        "claude": ("qwen_local", "openai"),
    })

    @classmethod
    def from_file(cls, path: Path) -> RoutingPolicy:
        raw = json.loads(path.read_text(encoding="utf-8"))
        allowed = {"task_preferences", "workflow_overrides", "fallback_order"}
        if not isinstance(raw, dict) or set(raw) - allowed:
            raise ValueError("Invalid routing policy keys")
        if any(not isinstance(raw.get(key, {}), dict) for key in ("task_preferences", "workflow_overrides", "fallback_order")):
            raise ValueError("Routing policy sections must be objects")
        default = cls()
        tasks = {**default.task_preferences, **raw.get("task_preferences", {})}
        workflows = raw.get("workflow_overrides", {})
        fallbacks = {**default.fallback_order, **raw.get("fallback_order", {})}
        for value in (*tasks.values(), *workflows.values()):
            if value not in {"qwen_local", "openai", "claude"}:
                raise ValueError("Unknown provider in routing policy")
        if set(fallbacks) - {"qwen_local", "openai", "claude"}:
            raise ValueError("Unknown fallback source")
        for values in fallbacks.values():
            if not isinstance(values, (list, tuple)) or any(value not in {"qwen_local", "openai", "claude"} for value in values):
                raise ValueError("Invalid fallback provider")
        return cls(tasks, workflows, {key: tuple(value) for key, value in fallbacks.items()})


def _enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be true or false")
    return value in {"true", "1", "yes"}


@dataclass(frozen=True)
class ModelSettings:
    default_brain: str = "qwen_local"
    qwen_enabled: bool = True
    qwen_base_url: str = "http://127.0.0.1:8080/v1"
    qwen_model: str = ""
    qwen_quantization: str = "Q4_K_S"
    openai_enabled: bool = False
    openai_model: str = ""
    claude_enabled: bool = False
    claude_model: str = ""
    allow_cloud_escalation: bool = False
    cloud_call_budget: int = 0
    cloud_budget_file: Path | None = None
    audit_file: Path | None = None
    policy: RoutingPolicy = field(default_factory=RoutingPolicy)

    @classmethod
    def from_env(cls) -> ModelSettings:
        policy_path = os.getenv("PY_DEV_POLICY_FILE")
        settings = cls(
            default_brain=os.getenv("DEFAULT_BRAIN", "qwen").strip().lower(),
            qwen_enabled=_enabled("QWEN_ENABLED", True),
            qwen_base_url=os.getenv("QWEN_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/"),
            qwen_model=os.getenv("QWEN_MODEL", "").strip(),
            qwen_quantization=os.getenv("QWEN_QUANTIZATION", "Q4_K_S").strip(),
            openai_enabled=_enabled("OPENAI_ENABLED") and _enabled("ALLOW_OPENAI"),
            openai_model=os.getenv("OPENAI_MODEL", "").strip(),
            claude_enabled=_enabled("CLAUDE_ENABLED") and _enabled("ALLOW_CLAUDE"),
            claude_model=os.getenv("CLAUDE_MODEL", "").strip(),
            allow_cloud_escalation=_enabled("ALLOW_CLOUD_ESCALATION"),
            cloud_call_budget=int(os.getenv("CLOUD_CALL_BUDGET", "0")),
            cloud_budget_file=Path(os.getenv("CLOUD_BUDGET_FILE", str(Path.home() / ".config" / "py-dev" / "cloud-budget.json"))).expanduser(),
            audit_file=Path(os.getenv("MODEL_AUDIT_FILE", str(Path.home() / ".config" / "py-dev" / "model-audit.jsonl"))).expanduser(),
            policy=RoutingPolicy.from_file(Path(policy_path)) if policy_path else RoutingPolicy(),
        )
        if settings.cloud_call_budget < 0:
            raise ValueError("CLOUD_CALL_BUDGET must be nonnegative")
        if settings.default_brain not in {"qwen", "qwen_local", "openai", "claude"}:
            raise ValueError("DEFAULT_BRAIN must be qwen, openai, or claude")
        return settings
