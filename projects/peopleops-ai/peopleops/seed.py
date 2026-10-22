from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from .config import PACKAGE, Settings, utcnow
from .db import audit, connect, initialize
from .pipeline import ingest
from .routing import route_request
from .workflows import deliver


def bootstrap(settings: Settings) -> dict:
    initialize(settings)
    with connect(settings) as conn:
        if conn.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone():
            return {"status": "already_initialized"}
    result = ingest(settings)
    with connect(settings) as conn:
        policies = json.loads((PACKAGE / "fixtures" / "policies.json").read_text())
        for policy in policies:
            conn.execute("INSERT OR IGNORE INTO policies VALUES(:policy_id,:title,:category,:visibility,:body,:version,:effective_date,:available)", policy)
        identities = []
        for principal_id, label, role, employee in [
            ("maya", "Maya Chen", "employee", "EMP-001"),
            ("jordan", "Jordan Lee", "employee", "EMP-002"),
            ("hr", "HR operator", "hr", None),
            ("analyst", "People analyst", "analyst", None),
        ]:
            token = secrets.token_urlsafe(32)
            conn.execute("INSERT OR IGNORE INTO principals VALUES(?,?,?,?,?)",
                         (principal_id, label, role, employee, hashlib.sha256(token.encode()).hexdigest()))
            identities.append(dict(principal_id=principal_id, label=label, role=role, employee_id=employee, token=token))
        settings.data_dir.mkdir(exist_ok=True)
        credentials = settings.data_dir / "demo-identities.json"
        credentials.write_text(json.dumps(identities, indent=2) + "\n")
        credentials.chmod(0o600)
        examples = [
            ("HR-001", "EMP-001", "Payroll help", "My payslip amount looks incorrect.", "open", "high", 4),
            ("HR-002", "EMP-002", "Benefits enrollment", "Where do I enroll in health benefits?", "in_progress", "normal", 3),
            ("HR-003", "EMP-003", "Vacation balance", "Please check my vacation balance.", "resolved", "normal", 6),
            ("HR-004", "EMP-011", "First week orientation", "How do I complete onboarding orientation?", "open", "normal", 1),
            ("HR-005", "EMP-004", "Update mailing address", "I need to update my address.", "open", "normal", 5),
            ("HR-006", "EMP-012", "New hire equipment", "My onboarding laptop has not arrived.", "in_progress", "high", 2),
        ]
        for request_id, employee_id, subject, description, status, priority, age in examples:
            routing = route_request(subject + " " + description)
            created = (datetime.now(timezone.utc) - timedelta(days=age)).isoformat()
            conn.execute("""INSERT OR IGNORE INTO hr_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (request_id, employee_id, subject, description, routing["category"], routing["team"], routing["confidence"],
                          status, priority, created, utcnow(), utcnow() if status == "resolved" else None, f"seed:{request_id}", "seed"))
        task = conn.execute("SELECT task_id FROM onboarding_tasks WHERE employee_id='EMP-011' ORDER BY kind LIMIT 1").fetchone()
        conn.execute("UPDATE onboarding_tasks SET status='completed',completed_at=? WHERE task_id=?", (utcnow(), task[0]))
        conn.execute("INSERT INTO meta VALUES('seeded',?)", (utcnow(),))
        audit(conn, "system", "demo.initialize", "database")
    deliver(settings)
    return result
