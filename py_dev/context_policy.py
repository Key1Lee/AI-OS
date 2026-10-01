"""Explicit, fail-closed context tier selection."""

from __future__ import annotations

from dataclasses import dataclass

from .local_runtime import LocalRuntimeReport
from .runtime_config import ResolvedConfig


class ContextLimitError(ValueError):
    pass


@dataclass(frozen=True)
class ContextPlan:
    tier: str
    limit_tokens: int
    estimated_prompt_tokens: int
    output_tokens: int
    reasoning_budget_tokens: int
    safety_margin_tokens: int


def estimate_tokens(text: str) -> int:
    # Deliberately conservative heuristic; actual API usage is traced later.
    return max(1, (len(text.encode("utf-8")) + 2) // 3)


def choose_context(config: ResolvedConfig, report: LocalRuntimeReport, *, prompt_text: str, reasoning_budget: int, output_tokens: int) -> ContextPlan:
    policy = config.values["context"]
    estimated = estimate_tokens(prompt_text) + 64
    margin = policy["safety_margin_tokens"]
    required = estimated + reasoning_budget + output_tokens + margin
    ceiling = min(policy["maximum_tokens"], report.model_context, report.runtime_context)
    forced = policy.get("tier")
    tiers = policy["tiers"]
    if forced:
        selected = forced
        size = tiers[selected]
        if size > ceiling:
            raise ContextLimitError(f"Requested {selected} context ({size}) exceeds verified capacity ({ceiling}); reduce the tier or restart llama-server with a validated context setting")
        if required > size:
            raise ContextLimitError(f"Prompt, reasoning allowance, and output need about {required} tokens, above the requested {selected} tier ({size}); reduce relevant context or choose a larger tier")
        return ContextPlan(selected, size, estimated, output_tokens, reasoning_budget, margin)
    for name, size in tiers.items():
        if size >= required and size <= ceiling:
            return ContextPlan(name, size, estimated, output_tokens, reasoning_budget, margin)
    raise ContextLimitError(f"Prompt, reasoning allowance, and output need about {required} tokens, above verified capacity ({ceiling}); retrieve less context or use a validated larger runtime")
