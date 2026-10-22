import csv
import io
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from survey_analytics.api import create_app
from survey_analytics.cohort import DEPARTMENTS, SURVEY_ID, cohort_fixture
from survey_analytics.fixture import export_fixture
from survey_analytics.mock_account import DEMO_API_TOKEN
from survey_analytics.pipeline import (
    ingest_bronze,
    inspect_layers,
    publish_gold,
    transform_silver,
)
from survey_analytics.visualization import get_cohort_gold, publish_visualization


def process(path, payload):
    bronze = ingest_bronze(path, payload)
    transform_silver(path, bronze["batch_id"])
    return publish_gold(path, bronze["batch_id"])


def test_distinct_employees_and_illustrative_roster():
    source = cohort_fixture()
    assert len(source["responses"]) == 5000
    assert len({r["responseId"] for r in source["responses"]}) == 5000
    assert len({r["values"]["employeeId"] for r in source["responses"]}) == 5000
    assert (
        Counter(r["values"]["department"] for r in source["responses"]) == DEPARTMENTS
    )
    source["responses"][0]["values"]["Q_CSAT"] = 999
    assert cohort_fixture()["responses"][0]["values"]["Q_CSAT"] != 999


def test_all_5000_and_independent_metric_arithmetic(tmp_path):
    path = tmp_path / "cohort.sqlite3"
    source = cohort_fixture()
    gold = process(path, source)
    assert gold["counts"] == {"invited": 5000, "valid_started": 5000, "completed": 5000}
    assert gold["metric_version"] == "survey-metrics-v2"
    assert len(gold["department_breakdown"]) == 10
    assert sum(s["counts"]["completed"] for s in gold["department_breakdown"]) == 5000
    assert gold["quality"]["quarantined_responses"] == 0
    for segment in [
        {"department": None, "metrics": gold["metrics"]},
        *gold["department_breakdown"],
    ]:
        rows = [
            r["values"]
            for r in source["responses"]
            if not segment["department"]
            or r["values"]["department"] == segment["department"]
        ]
        eng = [r["Q_ENGAGEMENT"] for r in rows if r["Q_ENGAGEMENT"] is not None]
        sat = [r["Q_CSAT"] for r in rows if r["Q_CSAT"] is not None]
        enps = [r["Q_ENPS"] for r in rows if r["Q_ENPS"] is not None]
        m = segment["metrics"]
        assert m["experience_score"]["value"] == round(sum(eng) / len(eng) * 20, 2)
        assert m["csat_top_two_box"]["value"] == round(
            sum(s >= 4 for s in sat) / len(sat) * 100, 2
        )
        assert m["enps"]["value"] == round(
            (sum(s >= 9 for s in enps) - sum(s <= 6 for s in enps)) / len(enps) * 100, 2
        )
    assert gold["metrics"]["experience_score"]["denominator"] == 4865
    assert gold["metrics"]["csat_top_two_box"]["denominator"] == 4828
    assert gold["metrics"]["enps"]["denominator"] == 4879
    before = inspect_layers(path)
    assert process(path, source)["replayed"] is True
    assert inspect_layers(path) == before


def test_both_fixtures_remain_isolated_and_export_aggregates(tmp_path):
    path = tmp_path / "both.sqlite3"
    old = process(path, export_fixture())
    gold = process(path, cohort_fixture())
    assert inspect_layers(path, old["batch_id"])["tables"]["silver_responses"] == 12
    assert inspect_layers(path, gold["batch_id"])["tables"]["silver_responses"] == 5000
    assert get_cohort_gold(path)["survey_id"] == SURVEY_ID
    with pytest.raises(ValueError):
        publish_visualization(path, old["batch_id"])
    report = publish_visualization(path, gold["batch_id"])
    html = Path(report["files"]["html"]).read_text()
    assert "R_SAM_SYNTH_" not in html and "EMP_SYNTH_" not in html
    assert "4865" in html and "survey-metrics-v2" in html
    rows = list(csv.DictReader(io.StringIO(Path(report["files"]["csv"]).read_text())))
    assert len(rows) == 10 and sum(int(r["responses"]) for r in rows) == 5000
    with pytest.raises(ValueError):
        publish_visualization(path, "../../outside")


def test_cohort_http_auth_empty_state_and_publication(tmp_path):
    with TestClient(create_app(tmp_path / "http.sqlite3")) as client:
        assert client.get("/dashboard").status_code == 200
        assert client.get("/analytics").status_code == 409
        assert (
            client.post(
                "/mock-qualtrics/exports", json={"dataset": "employees5000"}
            ).status_code
            == 401
        )
        headers = {"X-API-TOKEN": DEMO_API_TOKEN}
        assert (
            client.post(
                "/mock-qualtrics/exports", json={"dataset": "real"}, headers=headers
            ).status_code
            == 422
        )
        export = client.post(
            "/mock-qualtrics/exports",
            json={"dataset": "employees5000"},
            headers=headers,
        ).json()
        payload = client.get(
            f"/mock-qualtrics/exports/{export['export_id']}/file", headers=headers
        ).json()
        assert len(payload["responses"]) == 5000
        bronze = client.post("/layers/bronze", json=payload).json()
        batch = {"batch_id": bronze["batch_id"]}
        assert client.post("/analytics/publish", json=batch).status_code == 409
        assert client.post("/layers/silver", json=batch).status_code == 200
        assert client.post("/layers/gold", json=batch).status_code == 200
        report = client.post("/analytics/publish", json=batch).json()
        assert report["employees"] == 5000 and "files" not in report
        assert client.get(report["downloads"]["html"]).status_code == 200
        assert client.get(report["downloads"]["csv"]).text.count("True,") == 10
