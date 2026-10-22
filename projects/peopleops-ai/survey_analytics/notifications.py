"""Local operational inbox; accepts no error stack, source payload or credentials."""

from datetime import UTC, datetime

from .pipeline import connect


def ensure_inbox(db):
    """Create the local notification table without changing the data layers."""
    db.execute("""CREATE TABLE IF NOT EXISTS workflow_notifications (
        workflow_id TEXT, execution_id TEXT, last_node TEXT, received_at TEXT,
        PRIMARY KEY(workflow_id, execution_id))""")


def record_failure(path, event):
    """Record one safe operational notification per failed synthetic execution."""
    with connect(path) as db:
        ensure_inbox(db)
        db.execute(
            "INSERT OR IGNORE INTO workflow_notifications VALUES (?, ?, ?, ?)",
            (
                event.workflow_id,
                event.execution_id,
                event.last_node,
                datetime.now(UTC).isoformat(),
            ),
        )
    return {
        "status": "recorded",
        "channel": "local_inbox",
        "synthetic": True,
        "workflow_id": event.workflow_id,
        "execution_id": event.execution_id,
    }


def list_notifications(path):
    """Read the 100 most recent failure notifications without individual survey data."""
    with connect(path) as db:
        ensure_inbox(db)
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM workflow_notifications ORDER BY received_at DESC LIMIT 100"
            )
        ]
    return {"channel": "local_inbox", "synthetic": True, "notifications": rows}
