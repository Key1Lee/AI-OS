from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from data_system_map.contracts import DataEdge, DataNode, GraphSnapshot


class MetadataStore:
    """Atomic immutable snapshots; no trainer tables or candidate policy."""

    APPLICATION_ID = 0x444D4150

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size:
            with sqlite3.connect(f"file:{quote(str(path.resolve()))}?mode=ro", uri=True) as connection:
                tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tables and connection.execute("PRAGMA application_id").fetchone()[0] != self.APPLICATION_ID:
                    raise ValueError("The metadata profile belongs to another application; it was not changed.")
                if connection.execute("PRAGMA user_version").fetchone()[0] not in {0, 1}:
                    raise ValueError("The metadata profile uses an unsupported schema version.")
        with self.connection(write=True) as connection:
            connection.execute(f"PRAGMA application_id={self.APPLICATION_ID}")
            connection.execute("CREATE TABLE IF NOT EXISTS systems (id TEXT PRIMARY KEY, name TEXT NOT NULL, current_snapshot TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, system_id TEXT NOT NULL, created_at TEXT NOT NULL, body TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS nodes (snapshot_id TEXT REFERENCES snapshots(id), id TEXT, body TEXT NOT NULL, PRIMARY KEY(snapshot_id,id))")
            connection.execute("CREATE TABLE IF NOT EXISTS edges (snapshot_id TEXT REFERENCES snapshots(id), id TEXT, from_node TEXT NOT NULL, to_node TEXT NOT NULL, relationship TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(snapshot_id,id), FOREIGN KEY(snapshot_id,from_node) REFERENCES nodes(snapshot_id,id), FOREIGN KEY(snapshot_id,to_node) REFERENCES nodes(snapshot_id,id))")
            connection.execute("CREATE INDEX IF NOT EXISTS edges_from ON edges(snapshot_id,from_node)")
            connection.execute("CREATE INDEX IF NOT EXISTS edges_to ON edges(snapshot_id,to_node)")
            connection.execute("PRAGMA user_version=1")

    @contextmanager
    def connection(self, *, write=False):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def put(self, snapshot: GraphSnapshot) -> GraphSnapshot:
        body = snapshot.model_dump(exclude={"snapshot_id"})
        snapshot_id = hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest()
        stored = snapshot.model_copy(update={"snapshot_id": snapshot_id}, deep=True)
        header = stored.model_dump(exclude={"nodes", "edges"})
        with self.connection(write=True) as connection:
            if connection.execute("SELECT 1 FROM snapshots WHERE id=?", (snapshot_id,)).fetchone() is None:
                connection.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (snapshot_id, stored.system_id, datetime.now(timezone.utc).isoformat(), json.dumps(header, allow_nan=False)))
                connection.executemany("INSERT INTO nodes VALUES(?,?,?)", [(snapshot_id, n.id, n.model_dump_json()) for n in stored.nodes])
                connection.executemany("INSERT INTO edges VALUES(?,?,?,?,?,?)", [(snapshot_id, e.id, e.from_node, e.to_node, e.relationship_type, e.model_dump_json()) for e in stored.edges])
            connection.execute("INSERT INTO systems VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,current_snapshot=excluded.current_snapshot", (stored.system_id, stored.name, snapshot_id))
        return stored

    def get(self, system_id: str, snapshot_id: str | None = None) -> GraphSnapshot:
        with self.connection() as connection:
            system = connection.execute("SELECT * FROM systems WHERE id=?", (system_id,)).fetchone()
            if system is None:
                raise KeyError(system_id)
            identity = snapshot_id or system['current_snapshot']
            row = connection.execute("SELECT body FROM snapshots WHERE id=? AND system_id=?", (identity, system_id)).fetchone()
            if row is None:
                raise KeyError(identity)
            body = json.loads(row['body'])
            body['nodes'] = [DataNode.model_validate_json(r['body']).model_dump() for r in connection.execute("SELECT body FROM nodes WHERE snapshot_id=? ORDER BY id", (identity,))]
            body['edges'] = [DataEdge.model_validate_json(r['body']).model_dump() for r in connection.execute("SELECT body FROM edges WHERE snapshot_id=? ORDER BY id", (identity,))]
            return GraphSnapshot.model_validate(body)

    def systems(self) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM systems ORDER BY name,id")]

    def history(self, system_id: str) -> list[dict]:
        with self.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT id,created_at FROM snapshots WHERE system_id=? ORDER BY created_at,id", (system_id,))]
