"""Small, explicit configuration; no enterprise credentials are needed."""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import os

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parent


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("PEOPLEOPS_DATA_DIR", str(ROOT / "data"))).resolve())
    as_of: date = field(default_factory=lambda: date.fromisoformat(os.environ["PEOPLEOPS_AS_OF"]) if os.getenv("PEOPLEOPS_AS_OF") else datetime.now(ZoneInfo("Asia/Seoul")).date())
    demo_mode: bool = field(default_factory=lambda: os.getenv("PEOPLEOPS_DEMO_MODE", "1") == "1")
    retry_delay: float = 0.02

    @property
    def db_path(self) -> Path:
        return self.data_dir / "peopleops.db"

    @property
    def analytics_path(self) -> Path:
        return self.data_dir / "analytics.db"
