from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from .contracts import State

TRANSITIONS = {State.READY: State.BASELINE, State.BASELINE: State.FAULT_INJECTED,
               State.FAULT_INJECTED: State.FAILED, State.FAILED: State.DIAGNOSING,
               State.DIAGNOSING: State.REMEDIATED, State.REMEDIATED: State.VERIFIED,
               State.VERIFIED: State.MASTERED}

class StateError(ValueError):
    pass

class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "state.sqlite"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, document TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.database, timeout=30)

    def save(self, record: dict):
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?,?) ON CONFLICT(id) DO UPDATE SET document=excluded.document",
                       (record["run_id"], json.dumps(record)))

    def get(self, run_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT document FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise StateError(f"Unknown run {run_id}")
        return json.loads(row[0])

    def records(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT document FROM runs ORDER BY rowid DESC").fetchall()
        return [json.loads(r[0]) for r in rows]

    def transition(self, record: dict, state: State):
        current = State(record["state"])
        if TRANSITIONS.get(current) != state:
            raise StateError(f"Cannot move {current} → {state}")
        record["state"] = state.value
        record["transitions"].append({"from": current.value, "to": state.value})
        self.save(record)

    def invalidate(self, record: dict, reason: str):
        if record["state"] not in {State.VERIFIED, State.MASTERED}:
            raise StateError("Only a previously verified exercise can be invalidated")
        current = record["state"]
        record["state"] = State.REMEDIATED.value
        record["transitions"].append({"from": current, "to": State.REMEDIATED.value, "reason": reason})
        self.save(record)
