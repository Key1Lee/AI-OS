"""Project-local, atomically saved state and non-destructive reset archives."""
import fcntl
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .contracts import DIMENSIONS


def fresh_state(scenario):
    return {"schema_version": 1, "scenario_id": scenario["scenario_id"], "phase": "NEW",
            "released": [], "events": [], "submissions": [], "reviews": [],
            "exercise": None, "incident": False, "incident_passed": False,
            "recall_cursor": 0, "pending_recall": None, "hint_level": 0,
            "concepts": {key: {"state": "UNSEEN", "evidence": []}
                         for key in scenario["technical_concepts"]},
            "performance": {key: {"state": "UNSEEN", "evidence": []} for key in DIMENSIONS}}


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "state.json"

    @contextmanager
    def locked(self):
        with (self.directory / ".lock").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def read(self, scenario):
        if not self.path.exists():
            return fresh_state(scenario)
        data = json.loads(self.path.read_text())
        if data.get("schema_version") != 1 or data.get("scenario_id") != scenario["scenario_id"]:
            raise ValueError("Saved state is incompatible; preserve it and run fde reset")
        return data

    def write(self, data):
        fd, name = tempfile.mkstemp(prefix=".state-", dir=self.directory)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def reset(self, scenario):
        if self.path.exists() or (self.directory / "workspace").exists():
            history = self.directory / "history"
            history.mkdir(exist_ok=True)
            number = 1
            while (history / f"reset-{number:04d}").exists():
                number += 1
            archive = history / f"reset-{number:04d}"
            archive.mkdir()
            for name in ("state.json", "workspace"):
                source = self.directory / name
                if source.exists():
                    shutil.move(str(source), str(archive / name))
        state = fresh_state(scenario)
        self.write(state)
        return state
