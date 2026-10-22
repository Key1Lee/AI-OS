"""Idempotent synthetic identity/record loading into the demo SQLite database."""
import hashlib
import json

from app.mock_store import initialize, transaction
from app.models import PTORecord, Principal


def seed_enterprise_data(settings):
    """Seed changed fixture snapshots atomically; unchanged seeds preserve database edits."""
    initialize(settings.database_path)
    employees_raw = (settings.fixture_root/"employees.json").read_bytes()
    workday_raw = (settings.fixture_root/"workday_pto.json").read_bytes()
    employees = json.loads(employees_raw)
    records = json.loads(workday_raw)
    for entry in employees:
        Principal.model_validate(entry["principal"])
        if hashlib.sha256(entry["demo_token"].encode()).hexdigest() != entry["token_sha256"]:
            raise ValueError("Invalid synthetic session fixture")
    for record in records:
        PTORecord.model_validate(record)
    with transaction(settings.database_path, immediate=True) as conn:
        for kind, raw in [("employees", employees_raw), ("workday", workday_raw)]:
            digest = hashlib.sha256(raw).hexdigest()
            previous = conn.execute("SELECT digest FROM fixture_seeds WHERE kind=?", (kind,)).fetchone()
            if previous and previous[0] == digest:
                continue
            if kind == "employees":
                conn.execute("DELETE FROM mock_employees")
                conn.executemany("INSERT INTO mock_employees VALUES(?,?,?,?)", [
                    (e["principal"]["tenant"], e["principal"]["employee_id"], e["token_sha256"], json.dumps(e)) for e in employees])
            else:
                conn.execute("DELETE FROM mock_workday")
                conn.executemany("INSERT INTO mock_workday VALUES(?,?,?)", [
                    (r["tenant"], r["employee_id"], json.dumps(r)) for r in records])
            conn.execute("INSERT INTO fixture_seeds VALUES(?,?) ON CONFLICT(kind) DO UPDATE SET digest=excluded.digest", (kind, digest))
