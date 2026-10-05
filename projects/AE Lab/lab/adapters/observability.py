"""Translate measured Lab evidence through the existing observability facade."""
from __future__ import annotations

from pathlib import Path

from .bridge import invoke


class NativeObservabilityAdapter:
    def observe(self, evidence: dict, database: str) -> dict:
        if not database:
            raise ValueError("An isolated observability database is required.")
        return invoke("observability", {
            "operation": "observe", "evidence": evidence,
            "database": str(Path(database).resolve()),
        })

    def snapshot(self, database: str, snapshot_id: str) -> dict:
        """Read a pinned historic snapshot through the native public facade."""
        if not database or not snapshot_id:
            raise ValueError("An isolated database and snapshot identity are required.")
        return invoke("observability", {
            "operation": "snapshot", "database": str(Path(database).resolve()),
            "snapshot_id": snapshot_id,
        })
