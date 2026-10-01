"""Generic runtime configuration, independent of any consuming application."""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(default_factory=lambda: Path.cwd()/'data/observability.db')
    web_dist: Path = field(default_factory=lambda: Path.cwd()/'web/dist')

    @classmethod
    def from_env(cls, *, root: Path | None = None):
        root = root or Path.cwd()
        return cls(database_path=Path(os.environ.get('OBSERVABILITY_DB',str(root/'data/observability.db'))),
                   web_dist=Path(os.environ.get('OBSERVABILITY_WEB_DIST',str(root/'web/dist'))))
