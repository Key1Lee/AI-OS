"""Serialized adapter to the existing Data Quality & Contracts System."""
from __future__ import annotations

from .bridge import invoke


class NativeQualityAdapter:
    def validate(self, orders: list[dict], run_id: str, timestamp: str) -> dict:
        """Return native evidence; unavailable/invalid validation raises AdapterError."""
        return invoke("quality", {"orders": orders, "run_id": run_id, "timestamp": timestamp})
