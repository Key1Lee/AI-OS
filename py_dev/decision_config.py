"""Server-owned opt-in policy for the bounded decision provider."""
from dataclasses import dataclass
import os
from pathlib import Path

from .config import _enabled


@dataclass(frozen=True)
class DecisionSettings:
    enabled: bool = False
    model: str = ""
    daily_calls: int = 0
    budget_file: Path | None = None
    per_run_calls: int = 1

    @classmethod
    def from_env(cls):
        limit = int(os.getenv("AI_OS_JEV_DAILY_CALLS", "0"))
        run_limit = int(os.getenv("AI_OS_JEV_PER_RUN_CALLS", "1"))
        if limit < 0 or run_limit < 0:
            raise ValueError("Jev call limits must be nonnegative")
        return cls(_enabled("AI_OS_PROVIDER_JEV_ENABLED") and _enabled("ALLOW_JEV"),
                   os.getenv("JEV_MODEL", "").strip(), limit,
                   Path(os.getenv("AI_OS_JEV_BUDGET_FILE", str(Path.home() / ".config/py-dev/jev-budget.json"))).expanduser(), run_limit)
