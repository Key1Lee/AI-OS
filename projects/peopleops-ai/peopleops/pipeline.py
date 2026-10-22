from datetime import datetime
import json
from time import perf_counter
from uuid import uuid4
from .config import Settings, utcnow
from .db import audit, connect
from .integrations import MockWorkday, SourceFailure
from .validation import clean_employee
from .workflows import onboard


def ingest(settings: Settings, scenario="normal", volume=5000, actor="system") -> dict:
    run_id, started = str(uuid4()), perf_counter()
    source = MockWorkday(settings, scenario, volume)
    with connect(settings) as conn:
        conn.execute("INSERT INTO ingestion_runs(run_id,scenario,started_at,status) VALUES(?,?,?,'running')", (run_id, scenario, utcnow()))
    try:
        records = source.fetch()
        candidates, issues, duplicates = {}, [], 0
        for index, raw in enumerate(records, 1):
            try:
                employee = clean_employee(raw, settings.as_of)
            except ValueError as exc:
                raw_id = raw.get("employee_id")
                issues.append((index, str(raw_id)[:128] if raw_id is not None else None, str(exc)))
                continue
            key = employee["employee_id"]
            if key in candidates:
                duplicates += 1
                old_index, old = candidates[key]
                if datetime.fromisoformat(employee["source_updated_at"]) >= datetime.fromisoformat(old["source_updated_at"]):
                    issues.append((old_index, key, "duplicate_superseded"))
                else:
                    issues.append((index, key, "duplicate_superseded"))
                    continue
            candidates[key] = (index, employee)

        changed = unchanged = 0
        with connect(settings) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = {row["employee_id"]: dict(row) for row in conn.execute("SELECT * FROM employees")}
            # Remove broken manager references before any business rows are written.
            while True:
                invalid = [key for key, (_, row) in candidates.items()
                           if row["manager_id"] and row["manager_id"] not in candidates and row["manager_id"] not in existing]
                if not invalid:
                    break
                for key in invalid:
                    index, _ = candidates.pop(key)
                    issues.append((index, key, "unknown_manager"))
            email_owners = {row["email"]: key for key, row in existing.items()}
            for key in list(candidates):
                index, row = candidates[key]
                owner = email_owners.get(row["email"])
                if owner is not None and owner != key:
                    issues.append((index, key, "duplicate_email"))
                    del candidates[key]
                else:
                    email_owners[row["email"]] = key
            # A removed manager can invalidate dependent new hires as well.
            while True:
                invalid = [key for key, (_, row) in candidates.items()
                           if row["manager_id"] and row["manager_id"] not in candidates and row["manager_id"] not in existing]
                if not invalid:
                    break
                for key in invalid:
                    index, _ = candidates.pop(key)
                    issues.append((index, key, "unknown_manager"))
            for _, employee in candidates.values():
                old = existing.get(employee["employee_id"])
                if old and datetime.fromisoformat(employee["source_updated_at"]) <= datetime.fromisoformat(old["source_updated_at"]):
                    unchanged += 1
                    continue
                columns = list(employee) + ["synced_at"]
                values = list(employee.values()) + [utcnow()]
                updates = ",".join(f"{column}=excluded.{column}" for column in columns if column != "employee_id")
                conn.execute(f"INSERT INTO employees({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) ON CONFLICT(employee_id) DO UPDATE SET {updates}", values)
                onboard(conn, employee, settings)
                changed += 1
            conn.executemany("INSERT INTO raw_employees(run_id,row_number,payload) VALUES(?,?,?)",
                             [(run_id, i, json.dumps(row)) for i, row in enumerate(records, 1)])
            conn.executemany("INSERT INTO quarantine(run_id,row_number,employee_id,reason) VALUES(?,?,?,?)",
                             [(run_id, *issue) for issue in issues])
            rejected = len(issues) - duplicates
            latest = max((row["source_updated_at"] for _, row in candidates.values()), default=None)
            summary = dict(run_id=run_id, status="success", received=len(records), accepted=len(candidates),
                           rejected=rejected, duplicates=duplicates, changed=changed, unchanged=unchanged,
                           attempts=source.attempts, source_latest_at=latest,
                           duration_ms=round((perf_counter() - started) * 1000, 2))
            conn.execute("""UPDATE ingestion_runs SET status=:status,finished_at=:finished_at,received=:received,
                accepted=:accepted,rejected=:rejected,duplicates=:duplicates,changed=:changed,unchanged=:unchanged,
                attempts=:attempts,source_latest_at=:source_latest_at,duration_ms=:duration_ms WHERE run_id=:run_id""",
                {**summary, "finished_at": utcnow()})
            audit(conn, actor, "pipeline.run", run_id, scenario=scenario, accepted=len(candidates), rejected=rejected)
        return summary
    except Exception as exc:
        code = exc.code if isinstance(exc, SourceFailure) else "pipeline_error"
        with connect(settings) as conn:
            conn.execute("UPDATE ingestion_runs SET status='failed',finished_at=?,error_code=?,attempts=?,duration_ms=? WHERE run_id=?",
                         (utcnow(), code, source.attempts, round((perf_counter()-started)*1000, 2), run_id))
            audit(conn, actor, "pipeline.run", run_id, "failed", error_code=code)
        if not isinstance(exc, SourceFailure):
            raise
        return dict(run_id=run_id, status="failed", error_code=code, attempts=source.attempts)
