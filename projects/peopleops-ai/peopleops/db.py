from contextlib import contextmanager
import json
import sqlite3
from .config import PACKAGE, Settings, utcnow


@contextmanager
def connect(settings: Settings):
    """Open a filing cabinet; commit together or roll back together."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(settings: Settings):
    with connect(settings) as conn:
        conn.executescript((PACKAGE / "schema.sql").read_text())


def audit(conn, actor: str, action: str, target: str, outcome="allowed", **metadata):
    """Record actions, never ticket bodies, policy questions, salaries, or tokens."""
    conn.execute(
        "INSERT INTO audit_logs(created_at,actor,action,target,outcome,metadata) VALUES(?,?,?,?,?,?)",
        (utcnow(), actor, action, target, outcome, json.dumps(metadata)),
    )


def rows(conn, sql: str, params=()) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]
