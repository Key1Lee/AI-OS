from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.mark.requirement("HR-010", "HR-012", "HR-014", "HR-015")
def test_dashboard_job_runs_real_pytest_process(enterprise_settings):
    """An actual authenticated HTTP job runs the unit directory, not this end-to-end test."""
    settings = enterprise_settings.model_copy(update={"lab_job_timeout_seconds":30})
    canonical = Path(__file__).resolve().parents[2]/"reports/test-run.json"
    before = canonical.read_bytes() if canonical.exists() else None
    headers = {"Authorization":"Bearer demo-admin"}
    with TestClient(create_app(settings)) as client:
        response = client.post("/admin/test-runs", headers=headers, json={"suite":"unit"})
        assert response.status_code == 202
        job = response.json()
        deadline = time.monotonic()+35
        while job["status"] in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(.05)
            job = client.get("/admin/test-runs/"+job["job_id"], headers=headers).json()
        assert job["status"] == "passed", job
        assert job["tests"]["total"] > 10 and job["tests"]["failed"] == 0
        assert job["coverage_percent"] is not None and job["current_source"]
        assert "process.log" not in str(job) and "PRIVATE_API_KEY" not in str(job)
        assert (settings.lab_reports_path/job["job_id"]/"tests.xml").is_file()
    assert (canonical.read_bytes() if canonical.exists() else None) == before
