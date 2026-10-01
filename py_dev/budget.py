"""Conservative daily cloud-call budget for local Py.Dev processes."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path


class CloudCallBudget:
    def __init__(self, limit: int, path: Path | None = None):
        if limit < 0:
            raise ValueError("Cloud call budget must be nonnegative")
        self.limit = limit
        self.path = path
        self.used_in_memory = 0

    @staticmethod
    def _day() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _used(self) -> int:
        if self.path is None:
            return self.used_in_memory
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return 0
        except (OSError, ValueError):
            return self.limit  # Corrupt/unreadable ledger fails closed.
        if not isinstance(data, dict) or set(data) != {"date", "used"} or not isinstance(data["used"], int) or isinstance(data["used"], bool) or data["used"] < 0:
            return self.limit
        try:
            date.fromisoformat(data["date"])
        except (TypeError, ValueError):
            return self.limit
        return data["used"] if data["date"] == self._day() else 0

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self._used())

    def reserve(self) -> bool:
        if self.limit == 0:
            return False
        if self.path is None:
            if self.used_in_memory >= self.limit:
                return False
            self.used_in_memory += 1
            return True
        import fcntl

        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            lock_path = self.path.with_name(self.path.name + ".lock")
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            with os.fdopen(descriptor, "r+") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                used = self._used()
                if used >= self.limit:
                    return False
                payload = json.dumps({"date": self._day(), "used": used + 1})
                temp_descriptor, temp_name = tempfile.mkstemp(prefix=".budget-", dir=self.path.parent)
                try:
                    with os.fdopen(temp_descriptor, "w", encoding="utf-8") as output:
                        output.write(payload)
                        output.flush()
                        os.fsync(output.fileno())
                    os.replace(temp_name, self.path)
                finally:
                    if os.path.exists(temp_name):
                        os.unlink(temp_name)
                return True
        except OSError:
            return False
