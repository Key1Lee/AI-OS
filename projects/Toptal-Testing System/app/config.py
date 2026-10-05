from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from py_dev.providers.parsed import credential_configured


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    database_path: Path = PROJECT_ROOT / "data" / "assessment.db"
    host: str = "127.0.0.1"
    port: int = 8000
    interviewer_model: str = "gpt-6-sol"
    default_reasoning_effort: str = "medium"
    high_reasoning_effort: str = "high"
    openai_timeout_seconds: float = 90.0
    max_output_tokens: int = 5000
    openai_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        database = os.getenv("TOPTAL_TESTING_DB")
        return cls(
            database_path=(Path(database).expanduser().resolve() if database else PROJECT_ROOT / "data" / "assessment.db"),
            host=os.getenv("TOPTAL_TESTING_HOST", "127.0.0.1"),
            port=int(os.getenv("TOPTAL_TESTING_PORT", "8000")),
            interviewer_model=os.getenv("TOPTAL_TESTING_MODEL", "gpt-6-sol"),
            default_reasoning_effort=os.getenv("TOPTAL_TESTING_REASONING", "medium"),
            high_reasoning_effort=os.getenv("TOPTAL_TESTING_HIGH_REASONING", "high"),
            openai_timeout_seconds=float(os.getenv("TOPTAL_TESTING_OPENAI_TIMEOUT", "90")),
            max_output_tokens=int(os.getenv("TOPTAL_TESTING_MAX_OUTPUT_TOKENS", "5000")),
        )

    @property
    def api_configured(self) -> bool:
        # Legacy constructor field stays for existing injected test/workflow seams.
        # Production credentials are accessed exclusively by AI-OS.
        return bool(self.openai_api_key) or credential_configured("openai")
