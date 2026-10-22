from contextlib import contextmanager
from pathlib import Path
import sqlite3

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS registry (
 document_id TEXT NOT NULL, version TEXT NOT NULL, version_order INTEGER NOT NULL,
 metadata TEXT NOT NULL, digest TEXT NOT NULL,
 PRIMARY KEY(document_id,version));
CREATE TABLE IF NOT EXISTS indexed_documents (
 document_id TEXT NOT NULL, version TEXT NOT NULL, digest TEXT NOT NULL, full_text TEXT NOT NULL,
 PRIMARY KEY(document_id,version),
 FOREIGN KEY(document_id,version) REFERENCES registry(document_id,version));
CREATE TABLE IF NOT EXISTS inventory_membership (
 document_id TEXT NOT NULL, version TEXT NOT NULL, PRIMARY KEY(document_id,version));
CREATE TABLE IF NOT EXISTS chunks (
 chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, version TEXT NOT NULL,
 section TEXT NOT NULL, ordinal INTEGER NOT NULL, body TEXT NOT NULL,
 FOREIGN KEY(document_id,version) REFERENCES indexed_documents(document_id,version));
CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id,version);
CREATE TABLE IF NOT EXISTS ingestion_runs (
 run_id TEXT PRIMARY KEY, report TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS audits (
 sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL, event TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS receipts (
 tenant TEXT NOT NULL, actor TEXT NOT NULL, event_id TEXT NOT NULL,
 body_hash TEXT NOT NULL, response TEXT NOT NULL, expires_at REAL NOT NULL,
 PRIMARY KEY(tenant,actor,event_id));
CREATE TABLE IF NOT EXISTS mock_employees (
 tenant TEXT NOT NULL, employee_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
 entry TEXT NOT NULL, PRIMARY KEY(tenant,employee_id));
CREATE TABLE IF NOT EXISTS mock_workday (
 tenant TEXT NOT NULL, employee_id TEXT NOT NULL, record TEXT NOT NULL,
 PRIMARY KEY(tenant,employee_id));
CREATE TABLE IF NOT EXISTS fixture_seeds (
 kind TEXT PRIMARY KEY, digest TEXT NOT NULL);
"""


@contextmanager
def transaction(path: Path, immediate=False):
    """Open a short SQLite transaction and roll back all its changes on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path):
    """Create only the enterprise demo tables in its own SQLite file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(indexed_documents)")}
        if "full_text" not in columns:
            conn.execute("ALTER TABLE indexed_documents ADD COLUMN full_text TEXT NOT NULL DEFAULT ''")
