from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from py_dev.config import ModelSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    llm_mode: str = "auto"
    evaluator_provider: str = "auto"
    model: str = "gpt-5.6-sol"
    qwen_base_url: str = "http://127.0.0.1:1234/v1"
    qwen_model: str = "Qwen3.8-27B-UD-Q4_KS-C256K"
    qwen_api_key: str = "local"
    qwen_health_timeout_seconds: float = 1.5
    qwen_timeout_seconds: float = 90.0
    goal: str = "Senior forward-deployed engineering interview readiness"
    session_questions: int = 2
    failure_interval_days: float = 1.0
    hinted_interval_days: float = 3.0
    independent_interval_days: float = 7.0
    cold_recall_interval_days: float = 14.0
    transfer_interval_days: float = 30.0

    @classmethod
    def from_env(cls) -> "Settings":
        llm_mode = os.getenv("TRAINING_LLM_MODE", "auto").strip().lower()
        if llm_mode not in {"auto", "off", "required"}:
            raise ValueError("TRAINING_LLM_MODE must be auto, off, or required")
        evaluator_provider = os.getenv("EVALUATOR_PROVIDER", "auto").strip().lower()
        if evaluator_provider not in {
            "auto",
            "qwen_local",
            "openai",
            "offline_fallback",
        }:
            raise ValueError(
                "EVALUATOR_PROVIDER must be auto, qwen_local, openai, or offline_fallback"
            )
        # Preserve the original explicit offline switch unless the new selector
        # was deliberately configured.
        if llm_mode == "off" and "EVALUATOR_PROVIDER" not in os.environ:
            evaluator_provider = "offline_fallback"
        provider_settings = ModelSettings.from_env()
        return cls(
            database_path=Path(
                os.getenv("TRAINING_DB", str(PROJECT_ROOT / "data" / "training.db"))
            ).expanduser(),
            llm_mode=llm_mode,
            evaluator_provider=evaluator_provider,
            model=os.getenv("TRAINING_MODEL", "gpt-5.6-sol"),
            qwen_base_url=provider_settings.qwen_base_url,
            qwen_model=provider_settings.qwen_model,
            qwen_api_key="local",  # Deprecated compatibility field; loopback transport has no credential.
            qwen_health_timeout_seconds=max(
                0.1, float(os.getenv("QWEN_HEALTH_TIMEOUT_SECONDS", "1.5"))
            ),
            qwen_timeout_seconds=max(
                1.0, float(os.getenv("QWEN_TIMEOUT_SECONDS", "90"))
            ),
            goal=os.getenv(
                "TRAINING_GOAL",
                "Senior forward-deployed engineering interview readiness",
            ),
            session_questions=max(1, int(os.getenv("TRAINING_SESSION_QUESTIONS", "2"))),
        )
