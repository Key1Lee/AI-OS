"""Transactional outbox + an idempotent mock Slack receiver."""
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4
from .config import Settings, utcnow
from .db import audit, connect, rows


def enqueue(conn, event_key, event_type, payload):
    conn.execute("""INSERT INTO outbox(event_id,event_key,event_type,payload,status,created_at)
        VALUES(?,?,?,?,'pending',?) ON CONFLICT(event_key) DO NOTHING""",
        (str(uuid4()), event_key, event_type, json.dumps(payload), utcnow()))


def onboard(conn, employee: dict, settings: Settings):
    if employee["status"] not in {"active", "leave", "prehire"}:
        return
    if employee["hire_date"] < (settings.as_of - timedelta(days=30)).isoformat():
        return
    due = (datetime.fromisoformat(employee["hire_date"]).date() + timedelta(days=7)).isoformat()
    for kind, team in [("Verify profile", "People Operations"), ("Complete orientation", "People Operations"), ("Confirm equipment", "IT")]:
        conn.execute("""INSERT INTO onboarding_tasks(task_id,employee_id,kind,owner_team,status,due_date)
            VALUES(?,?,?,?,'pending',?) ON CONFLICT(employee_id,kind) DO NOTHING""",
            (str(uuid4()), employee["employee_id"], kind, team, due))
    enqueue(conn, f"onboarding:{employee['employee_id']}", "onboarding", {"employee_id": employee["employee_id"], "tasks": 3})


def queue_reminders(settings: Settings, actor="system") -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    with connect(settings) as conn:
        tickets = rows(conn, "SELECT request_id FROM hr_requests WHERE status != 'resolved' AND created_at < ?", (cutoff,))
        before = conn.total_changes
        for ticket in tickets:
            enqueue(conn, f"reminder:{ticket['request_id']}:{settings.as_of}", "reminder", {"request_id": ticket["request_id"]})
        queued = conn.total_changes - before
        audit(conn, actor, "reminders.queue", "outbox", count=queued)
    return {"eligible": len(tickets), "queued": queued}


def deliver(settings: Settings, failures=0, actor="system") -> dict:
    """A failed message is retained; another drain retries the same event key."""
    sent = failed = 0
    with connect(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        pending = rows(conn, "SELECT * FROM outbox WHERE status != 'sent' ORDER BY created_at,event_id LIMIT 500")
        for event in pending:
            success = False
            attempts = event["attempts"]
            for _ in range(3):
                attempts += 1
                if failures > 0:
                    failures -= 1
                    continue
                payload = json.loads(event["payload"])
                if event["event_type"] == "onboarding":
                    text = f"Onboarding ready: {payload['employee_id']} · {payload['tasks']} tasks."
                    channel = "#people-onboarding"
                else:
                    text = f"HR request {payload['request_id']} needs follow-up. Open the secure HR queue."
                    channel = "#hr-follow-up"
                # Receiver deduplicates event_key. In this local simulator both writes commit together.
                conn.execute("""INSERT INTO slack_messages(message_id,event_key,channel,text,created_at)
                    VALUES(?,?,?,?,?) ON CONFLICT(event_key) DO NOTHING""",
                    (str(uuid4()), event["event_key"], channel, text, utcnow()))
                conn.execute("UPDATE outbox SET status='sent',attempts=?,delivered_at=?,error_code=NULL WHERE event_id=?",
                             (attempts, utcnow(), event["event_id"]))
                success = True
                sent += 1
                break
            if not success:
                conn.execute("UPDATE outbox SET status='failed',attempts=?,error_code='mock_slack_unavailable' WHERE event_id=?",
                             (attempts, event["event_id"]))
                failed += 1
        audit(conn, actor, "notifications.drain", "outbox", sent=sent, failed=failed)
    return {"sent": sent, "failed": failed, "remaining": len(pending) - sent}
