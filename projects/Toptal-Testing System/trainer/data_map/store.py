from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote


class MapConflict(ValueError):
    pass


class InvestigationStore:
    APPLICATION_ID = 0x444D5452

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size:
            with sqlite3.connect(f"file:{quote(str(path.resolve()))}?mode=ro", uri=True) as connection:
                tables = list(connection.execute("SELECT name FROM sqlite_master WHERE type='table'"))
                if tables and connection.execute('PRAGMA application_id').fetchone()[0] != self.APPLICATION_ID:
                    raise ValueError("The investigation profile belongs to another application; it was not changed.")
                if connection.execute('PRAGMA user_version').fetchone()[0] not in {0,1}:
                    raise ValueError("The investigation profile schema is unsupported.")
        with self.connection(write=True) as connection:
            connection.execute(f'PRAGMA application_id={self.APPLICATION_ID}')
            connection.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, system_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, independent INTEGER NOT NULL, draft TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, result TEXT)')
            connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS one_active_session ON sessions(status) WHERE status="active"')
            connection.execute('CREATE TABLE IF NOT EXISTS actions (sequence INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id), kind TEXT NOT NULL, target TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS submissions (request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), body TEXT NOT NULL, result TEXT NOT NULL)')
            connection.execute('PRAGMA user_version=1')

    @contextmanager
    def connection(self, *, write=False):
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def view(self, connection, row) -> dict:
        if row is None:
            raise KeyError('session')
        value = dict(row)
        value['independent'] = bool(value['independent'])
        value['draft'] = json.loads(value['draft'])
        value['result'] = json.loads(value['result']) if value['result'] else None
        value['actions'] = [{**dict(item), 'payload': json.loads(item['payload'])} for item in connection.execute('SELECT * FROM actions WHERE session_id=? ORDER BY sequence', (value['id'],))]
        return value
