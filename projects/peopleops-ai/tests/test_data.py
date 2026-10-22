from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import sqlite3
import pytest
from peopleops.analytics import freshness, metrics, quality_checks
from peopleops.db import connect
from peopleops.integrations import source_records
from peopleops.pipeline import ingest
from peopleops.seed import bootstrap
from peopleops.validation import clean_employee, parse_date


def test_seed_business_outcomes(settings):
    with connect(settings) as conn:
        m = metrics(conn, settings)
        assert (m["headcount"],m["new_hires_30d"],m["departures_30d"],m["unresolved_requests"]) == (14,5,1,5)
        assert (m["total_tasks"],m["completed_tasks"],m["onboarding_completion_pct"]) == (15,1,6.7)
        run = conn.execute("SELECT * FROM ingestion_runs").fetchone()
        assert (run["received"],run["accepted"],run["rejected"],run["duplicates"]) == (22,16,4,2)
        assert conn.execute("SELECT email FROM employees WHERE employee_id='EMP-002'").fetchone()[0] == "jordan.lee@fictional.example"
        assert len(conn.execute("SELECT * FROM quarantine").fetchall()) == 6
        assert all(c["passed"] for c in quality_checks(conn))


def test_replay_is_incremental_and_preserves_state(settings):
    result = ingest(settings)
    assert (result["changed"],result["unchanged"]) == (0,16)
    assert bootstrap(settings)["status"] == "already_initialized"
    with connect(settings) as conn:
        assert conn.execute("SELECT COUNT(*) FROM onboarding_tasks").fetchone()[0] == 15
        assert conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 5


@pytest.mark.parametrize("scenario,expected,attempts",[("transient","success",3),("unavailable","failed",3),("malformed","failed",1)])
def test_failures_retries_and_state_preservation(settings, scenario, expected, attempts):
    result = ingest(settings,scenario)
    assert result["status"] == expected
    assert result["attempts"] == attempts
    with connect(settings) as conn:
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 16
        if expected == "failed":
            assert conn.execute("SELECT COUNT(*) FROM raw_employees WHERE run_id=?",(result["run_id"],)).fetchone()[0] == 0


def test_stale_input_alerts_without_regressing_employee_versions(settings):
    with connect(settings) as conn:
        before = conn.execute("SELECT source_updated_at FROM employees WHERE employee_id='EMP-001'").fetchone()[0]
    result = ingest(settings,"stale")
    assert result["changed"] == 0
    with connect(settings) as conn:
        assert freshness(conn)["state"] == "stale"
        assert conn.execute("SELECT source_updated_at FROM employees WHERE employee_id='EMP-001'").fetchone()[0] == before
    ingest(settings)
    with connect(settings) as conn:
        assert freshness(conn)["state"] == "fresh"


def test_new_hire_event_concurrent_replay(settings):
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: ingest(settings,"new_hire"),range(2)))
    assert sum(r["changed"] for r in results) == 1
    with connect(settings) as conn:
        assert conn.execute("SELECT COUNT(*) FROM onboarding_tasks WHERE employee_id='EMP-021'").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM outbox WHERE event_key='onboarding:EMP-021'").fetchone()[0] == 1


def test_pipeline_atomic_rollback(settings,monkeypatch):
    def fail(*args):
        raise RuntimeError("simulated_internal_failure")
    monkeypatch.setattr("peopleops.pipeline.onboard",fail)
    with pytest.raises(RuntimeError):
        ingest(settings,"new_hire")
    with connect(settings) as conn:
        assert not conn.execute("SELECT 1 FROM employees WHERE employee_id='EMP-021'").fetchone()
        assert conn.execute("SELECT status FROM ingestion_runs ORDER BY rowid DESC LIMIT 1").fetchone()[0] == "failed"


def test_growth_volume(settings):
    result = ingest(settings,"growth",5000)
    assert result["received"] == 5001
    assert result["accepted"] == 4995
    assert result["received"] == result["accepted"] + result["rejected"] + result["duplicates"]
    with connect(settings) as conn:
        assert conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 4995
        assert all(c["passed"] for c in quality_checks(conn))


@pytest.mark.parametrize("field,value,reason",[
    ("full_name","", "missing_required_field"),("email",None,"invalid_email"),
    ("hire_date","2026-02-30","invalid_date"),("status","mystery","invalid_status"),
    ("salary_cents",-1,"invalid_salary"),("salary_cents",True,"invalid_salary"),
    ("source_updated_at","2026-10-01","invalid_source_timestamp"),
    ("manager_id","EMP-001","self_manager"),
])
def test_bad_source_rows(settings,field,value,reason):
    raw = source_records(settings)[0]
    raw[field] = value
    with pytest.raises(ValueError,match=reason):
        clean_employee(raw,settings.as_of)


def test_date_normalization():
    assert parse_date("04/01/2024") == "2024-04-01"


def test_future_hire_cannot_be_active(settings):
    raw = source_records(settings)[0]
    raw["hire_date"] = (settings.as_of+timedelta(days=1)).isoformat()
    with pytest.raises(ValueError,match="future_active_hire"):
        clean_employee(raw,settings.as_of)


def test_unknown_manager_quarantined(settings,monkeypatch):
    record = {**source_records(settings)[0],"employee_id":"EMP-099","email":"unknown@fictional.example","manager_id":"EMP-999"}
    monkeypatch.setattr("peopleops.integrations.MockWorkday.fetch",lambda self:[record])
    result = ingest(settings)
    assert (result["accepted"],result["rejected"]) == (0,1)
    with connect(settings) as conn:
        assert conn.execute("SELECT reason FROM quarantine WHERE run_id=?",(result["run_id"],)).fetchone()[0] == "unknown_manager"


def test_quality_detection_catches_incorrect_reconciliation(settings):
    with connect(settings) as conn:
        conn.execute("UPDATE ingestion_runs SET received=received+1")
    with connect(settings) as conn:
        failures = [c["name"] for c in quality_checks(conn) if not c["passed"]]
        assert failures == ["Pipeline row counts reconcile"]


def test_foreign_keys_enforced(settings):
    with pytest.raises(sqlite3.IntegrityError):
        with connect(settings) as conn:
            conn.execute("UPDATE employees SET manager_id='EMP-999' WHERE employee_id='EMP-002'")


def test_non_scalar_invalid_id_is_quarantined(settings,monkeypatch):
    record = {**source_records(settings)[0],"employee_id":{"malformed":"identifier"}}
    monkeypatch.setattr("peopleops.integrations.MockWorkday.fetch",lambda self:[record])
    result = ingest(settings)
    assert (result["status"],result["accepted"],result["rejected"]) == ("success",0,1)
