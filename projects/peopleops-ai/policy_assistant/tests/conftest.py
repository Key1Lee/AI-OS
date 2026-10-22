import hashlib
import json
import os
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import create_app
from app.config import Settings
from app.providers import Providers
from app.storage import connect, initialize

ROOT = Path(__file__).resolve().parents[1]
TOKENS = {"employee": "test-employee-token", "gb": "test-gb-token", "hr": "test-hr-token", "admin": "test-admin-token", "other": "test-other-tenant-token"}


@pytest.fixture
def settings():
    credentials = []
    for name, token in TOKENS.items():
        credentials.append({"token_sha256": hashlib.sha256(token.encode()).hexdigest(), "identity": {
            "subject": name, "tenant": "other" if name == "other" else "fictional-acme", "region": "GB" if name == "gb" else "US",
            "role": name if name in ("hr", "admin") else "employee"}})
    return Settings(_env_file=None, database_url=SecretStr(os.environ.get("TEST_DATABASE_URL", "postgresql://test:test-local-only@127.0.0.1:55434/peopleops_policy_test")),
                    auth_credentials=SecretStr(json.dumps(credentials)), llm_provider="mock", embedding_provider="mock",
                    provider_api_key=SecretStr(""), allow_external_provider=False, embedding_dimensions=256, top_k=5, min_similarity=0.18)


@pytest.fixture
def database(settings):
    database_name = psycopg.conninfo.conninfo_to_dict(settings.database_url.get_secret_value()).get("dbname", "")
    if not database_name.endswith("_test"):
        raise RuntimeError("Tests require a separate database ending in _test")
    initialize(settings)
    with connect(settings) as conn:
        conn.execute("TRUNCATE policy_audit, policy_chunks, policy_documents RESTART IDENTITY")
    yield settings


@pytest.fixture
def providers(settings):
    return Providers(settings)


@pytest.fixture
def client(database, providers):
    with TestClient(create_app(database, providers)) as client:
        yield client


def headers(name="employee"):
    return {"Authorization": "Bearer " + TOKENS[name]}


def file_payload(filename):
    return {"filename": filename, "markdown": (ROOT / "policies" / filename).read_text()}


def ingest_files(client, *filenames):
    response = client.post("/admin/ingest", headers=headers("admin"), json={"documents": [file_payload(f) for f in filenames]})
    assert response.status_code == 200, response.text
    return response.json()


# Standalone enterprise tests never request the PostgreSQL fixtures above.
@pytest.fixture
def enterprise_settings(tmp_path):
    from app.settings import HRSettings
    return HRSettings(database_path=tmp_path / "enterprise.sqlite3", lab_reports_path=tmp_path/"lab", max_requests_per_minute=10000)


@pytest.fixture
def hr_client(enterprise_settings):
    from app.main import create_app as create_enterprise_app
    with TestClient(create_enterprise_app(enterprise_settings)) as client:
        yield client


_enterprise_test_results = []
_enterprise_start_fingerprint = None


def pytest_sessionstart(session):
    global _enterprise_start_fingerprint
    from evals.provenance import fingerprint
    _enterprise_test_results.clear()
    _enterprise_start_fingerprint = fingerprint()


def pytest_runtest_logreport(report):
    if report.when == "call":
        _enterprise_test_results.append({"nodeid": report.nodeid, "outcome": report.outcome})


def pytest_sessionfinish(session, exitstatus):
    from evals.provenance import fingerprint
    directory = Path(os.environ.get("HR_TEST_REPORT_DIR", ROOT / "reports"))
    directory.mkdir(parents=True, exist_ok=True)
    final_fingerprint = fingerprint()
    (directory / "test-run.json").write_text(json.dumps({"exit_status": int(exitstatus), "source_fingerprint": final_fingerprint,
        "start_fingerprint": _enterprise_start_fingerprint, "source_matches_run_start": final_fingerprint == _enterprise_start_fingerprint,
        "tests": _enterprise_test_results}, indent=2))
