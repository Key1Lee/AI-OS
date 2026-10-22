from datetime import datetime, timedelta, timezone
from .config import Settings, utcnow
from .db import rows


def metrics(conn, settings: Settings) -> dict:
    today = settings.as_of.isoformat()
    start = (settings.as_of - timedelta(days=29)).isoformat()
    workforce = dict(conn.execute("""SELECT
        COUNT(*) AS records,
        SUM(CASE WHEN status IN ('active','leave') AND hire_date <= :today THEN 1 ELSE 0 END) AS headcount,
        SUM(CASE WHEN status='leave' THEN 1 ELSE 0 END) AS on_leave,
        SUM(CASE WHEN status='prehire' THEN 1 ELSE 0 END) AS prehires,
        SUM(CASE WHEN hire_date BETWEEN :start AND :today AND status!='prehire' THEN 1 ELSE 0 END) AS new_hires_30d,
        SUM(CASE WHEN termination_date BETWEEN :start AND :today THEN 1 ELSE 0 END) AS departures_30d
        FROM employees""", {"today": today, "start": start}).fetchone())
    requests = dict(conn.execute("""SELECT COUNT(*) AS total_requests,
        COALESCE(SUM(status != 'resolved'),0) AS unresolved_requests,
        COALESCE(SUM(status = 'resolved'),0) AS resolved_requests FROM hr_requests""").fetchone())
    onboarding = dict(conn.execute("""SELECT COUNT(*) AS total_tasks,
        COALESCE(SUM(status='completed'),0) AS completed_tasks FROM onboarding_tasks""").fetchone())
    total = onboarding["total_tasks"]
    return {**workforce, **requests, **onboarding,
            "onboarding_completion_pct": round(onboarding["completed_tasks"] / total * 100, 1) if total else 0,
            "as_of": today, "window_start": start, "generated_at": utcnow(),
            "departments": rows(conn, """SELECT department,COUNT(*) AS headcount FROM employees
                WHERE status IN ('active','leave') AND hire_date<=? GROUP BY department ORDER BY headcount DESC,department""", (today,)),
            "request_categories": rows(conn, """SELECT category,COUNT(*) AS count FROM hr_requests
                WHERE status!='resolved' GROUP BY category ORDER BY count DESC,category""")}


def freshness(conn) -> dict:
    latest = conn.execute("SELECT * FROM ingestion_runs WHERE status='success' ORDER BY finished_at DESC,rowid DESC LIMIT 1").fetchone()
    recent = conn.execute("SELECT status,error_code FROM ingestion_runs ORDER BY started_at DESC,rowid DESC LIMIT 1").fetchone()
    if not latest or not latest["source_latest_at"]:
        return {"state": "missing", "source_age_hours": None, "sync_age_hours": None, "latest_run_status": recent["status"] if recent else None}
    now = datetime.now(timezone.utc)
    source_age = max(0, (now - datetime.fromisoformat(latest["source_latest_at"])).total_seconds()/3600)
    sync_age = max(0, (now - datetime.fromisoformat(latest["finished_at"])).total_seconds()/3600)
    return {"state": "stale" if source_age > 48 or sync_age > 24 else "fresh",
            "source_age_hours": round(source_age, 1), "sync_age_hours": round(sync_age, 1),
            "latest_run_status": recent["status"], "last_success": latest["finished_at"]}


def quality_checks(conn) -> list[dict]:
    checks = [
        ("Foreign key relationships", len(conn.execute("PRAGMA foreign_key_check").fetchall())),
        ("Employee IDs are unique", conn.execute("SELECT COUNT(*)-COUNT(DISTINCT employee_id) FROM employees").fetchone()[0]),
        ("Emails are normalized", conn.execute("SELECT COUNT(*) FROM employees WHERE email != lower(trim(email)) OR email NOT LIKE '%@%.%'").fetchone()[0]),
        ("Employment status and departure agree", conn.execute("SELECT COUNT(*) FROM employees WHERE (status='terminated') != (termination_date IS NOT NULL)").fetchone()[0]),
        ("Pipeline row counts reconcile", conn.execute("SELECT COUNT(*) FROM ingestion_runs WHERE status='success' AND received != accepted+rejected+duplicates").fetchone()[0]),
        ("No duplicate onboarding tasks", conn.execute("SELECT COUNT(*) FROM (SELECT employee_id,kind FROM onboarding_tasks GROUP BY employee_id,kind HAVING COUNT(*)>1)").fetchone()[0]),
        ("Resolved requests have completion dates", conn.execute("SELECT COUNT(*) FROM hr_requests WHERE (status='resolved') != (resolved_at IS NOT NULL)").fetchone()[0]),
    ]
    result = [dict(name=name, failures=failures, passed=failures == 0) for name, failures in checks]
    state = freshness(conn)
    result.append(dict(name="Workday data freshness", failures=int(state["state"] != "fresh"), passed=state["state"] == "fresh"))
    return result


def operations(conn) -> dict:
    observations = rows(conn, "SELECT status_code,duration_ms FROM http_observations ORDER BY id DESC LIMIT 1000")
    latencies = sorted(row["duration_ms"] for row in observations)
    server_errors = sum(row["status_code"] >= 500 for row in observations)
    return {"freshness": freshness(conn), "quality": quality_checks(conn),
            "runs": rows(conn, "SELECT * FROM ingestion_runs ORDER BY started_at DESC,rowid DESC LIMIT 12"),
            "quarantine": rows(conn, """SELECT reason,COUNT(*) AS count FROM quarantine
                WHERE run_id=(SELECT run_id FROM ingestion_runs WHERE status='success' ORDER BY finished_at DESC,rowid DESC LIMIT 1)
                GROUP BY reason ORDER BY count DESC"""),
            "outbox": rows(conn, "SELECT status,COUNT(*) AS count FROM outbox GROUP BY status"),
            "http": {"sample_size": len(observations), "server_errors": server_errors,
                     "availability_pct": round((1-server_errors/len(observations))*100, 2) if observations else None,
                     "p95_ms": round(latencies[min(len(latencies)-1, int(len(latencies)*.95))], 2) if latencies else None}}
