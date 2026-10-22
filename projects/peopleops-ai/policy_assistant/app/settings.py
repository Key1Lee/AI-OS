"""Configuration for the standalone SQLite enterprise demonstration."""
from datetime import date
import os
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml

ROOT = Path(__file__).resolve().parents[1]


class HRSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HR_", extra="forbid")
    database_path: Path = ROOT / "data/enterprise.sqlite3"
    fixture_root: Path = ROOT / "mock_data"
    rules_root: Path = ROOT / "config"
    lab_enabled: bool = True
    lab_reports_path: Path = ROOT / "reports/lab"
    lab_job_timeout_seconds: int = Field(default=120, ge=5, le=300)
    as_of_date: date = date(2026, 10, 20)
    demo_mode: bool = True
    slack_signing_secret: SecretStr = SecretStr("fictional-local-slack-signing-secret")
    slack_max_age_seconds: int = Field(default=300, ge=1, le=300)
    chunk_chars: int = Field(default=600, ge=120, le=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    min_relevance: float = Field(default=0.12, ge=0, le=1)
    max_record_age_days: int = Field(default=7, ge=0, le=30)
    workday_timeout_seconds: float = Field(default=0.1, gt=0, le=2)
    workday_attempts: int = Field(default=3, ge=1, le=3)
    workday_backoff_seconds: float = Field(default=0.005, ge=0, le=0.2)
    max_requests_per_minute: int = Field(default=120, ge=1, le=10000)
    receipt_ttl_seconds: int = Field(default=86400, ge=1, le=86400)
    evaluation_gates: dict[str, float] = Field(default_factory=lambda: {
        "routing_accuracy": 0.98, "recall_at_5": 0.95, "citation_validity": 1,
        "extractive_support": 0.98, "security_pass_rate": 1, "pto_exactness": 1,
        "mock_p95_ms": 750, "coverage_percent": 85})

    @classmethod
    def configured(cls):
        """Read project YAML defaults while giving explicit environment values precedence."""
        data = yaml.safe_load((ROOT / "config/app.yaml").read_text())
        values = {k: v for k, v in data.items() if "HR_" + k.upper() not in os.environ}
        return cls(**values)
