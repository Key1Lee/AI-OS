"""Metadata-only attribution for shared intelligence and decision calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


class EventSink:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(os.getenv("AI_OS_EVENT_FILE", str(Path.home() / ".config/py-dev/intelligence-events.jsonl"))).expanduser()

    def __call__(self, event: Mapping[str, Any]) -> None:
        # Call sites construct whitelist events. Do not pass arbitrary provider objects.
        payload = json.dumps(dict(event), allow_nan=False, separators=(",", ":")) + "\n"
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
