from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    database_path: Path = ROOT / "data" / "ae-trainer.db"
    execution_timeout: float = 5.0
    suite_timeout: float = 30.0
    max_rows: int = 1000

    def __post_init__(self):
        if not 0 < self.execution_timeout <= 30 or not 0 < self.suite_timeout <= 90:
            raise ValueError("Execution limits must be positive and bounded (30s query / 90s suite).")
        if not 0 < self.max_rows <= 1000:
            raise ValueError("Result row limit must be between 1 and 1000.")

    @classmethod
    def from_env(cls) -> "Settings":
        path = os.getenv("AE_TRAINER_DB")
        return cls(
            database_path=Path(path).expanduser().resolve() if path else ROOT / "data" / "ae-trainer.db",
            execution_timeout=float(os.getenv("AE_SQL_TIMEOUT", "5")),
        )
