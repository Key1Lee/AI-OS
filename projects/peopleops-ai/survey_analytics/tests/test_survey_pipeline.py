import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from survey_analytics.api import create_app
from survey_analytics.fixture import export_fixture
from survey_analytics.mock_account import DEMO_API_TOKEN
from survey_analytics.pipeline import (
    connect,
    ingest_bronze,
    inspect_layers,
    publish_gold,
    score_metrics,
    transform_silver,
    validate_response,
)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "survey.sqlite3"


def run(path):
    bronze = ingest_bronze(path, export_fixture())
    silver = transform_silver(path, bronze["batch_id"])
    return bronze, silver, publish_gold(path, bronze["batch_id"])


def test_counts_and_latest_revision(path):
    bronze, silver, gold = run(path)
    assert (
        bronze["raw_deliveries"],
        bronze["unique_versions"],
        bronze["duplicate_deliveries"],
    ) == (15, 14, 1)
    assert (
        silver["accepted_responses"],
        silver["quarantined_responses"],
        silver["superseded_versions"],
    ) == (12, 1, 1)
    assert silver["quarantine"] == [
        {"response_id": "R_SYNTH_BAD", "reason": "Q_ENGAGEMENT outside 1..5"}
    ]
    with connect(path) as db:
        row = db.execute(
            "SELECT payload FROM silver_responses WHERE response_id='R_SYNTH_002'"
        ).fetchone()
    assert json.loads(row[0])["engagement"] == 4
    assert gold["counts"] == {"invited": 20, "valid_started": 12, "completed": 10}


def test_gold_metrics_and_question_specific_denominators(path):
    _, _, gold = run(path)
    m = gold["metrics"]
    assert m["response_rate"]["value"] == 50
    assert m["completion_rate"]["value"] == 83.33
    assert m["engagement_mean"] == {
        "value": 3.9,
        "numerator": 39,
        "denominator": 10,
        "unit": "score_1_to_5",
    }
    assert m["engagement_favorable"]["value"] == 70
    assert m["csat_top_two_box"]["value"] == 77.78
    assert m["csat_top_two_box"]["denominator"] == 9
    assert m["enps"]["value"] == 22.22
    assert (
        m["enps"]["promoters"],
        m["enps"]["detractors"],
        m["enps"]["denominator"],
    ) == (4, 2, 9)
    assert m["median_completion_seconds"] == 195


def test_replay_preserves_rows_and_business_results(path):
    first = run(path)
    before = inspect_layers(path)
    second = run(path)
    assert inspect_layers(path) == before
    assert all(stage["replayed"] for stage in second)
    assert {**first[2], "replayed": True} == second[2]
    assert before["tables"] == {
        "bronze_batches": 1,
        "bronze_responses": 14,
        "silver_responses": 12,
        "quarantine": 1,
        "gold_snapshots": 1,
    }


def test_concurrent_retries_publish_one_snapshot(path):
    # Initialize tables before competing writers; each stage takes an immediate lock.
    with connect(path):
        pass
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: run(path)[2], range(8)))
    assert len({r["batch_id"] for r in results}) == 1
    assert sum(not r["replayed"] for r in results) == 1
    assert inspect_layers(path)["tables"]["gold_snapshots"] == 1


def test_empty_answers_are_null_not_invented_zero():
    for answer in score_metrics([]).values():
        if isinstance(answer, dict):
            assert answer["value"] is None and answer["denominator"] == 0
        else:
            assert answer is None


def test_no_department_subtraction_disclosure(path):
    _, _, gold = run(path)
    assert gold["department_breakdown"] == []
    assert gold["privacy"]["department_slices_suppressed"] is True
    assert "responseId" not in json.dumps(gold)
    assert "R_SYNTH" not in json.dumps(gold)


@pytest.mark.parametrize(
    "key,value",
    [
        ("Q_ENGAGEMENT", 0),
        ("Q_ENGAGEMENT", True),
        ("Q_CSAT", 6),
        ("Q_ENPS", 11),
        ("finished", "true"),
        ("recordedDate", "2026-10-20T09:00:00"),
        ("durationSeconds", -1),
    ],
)
def test_bad_schema_rejected(key, value):
    row = deepcopy(export_fixture()["responses"][0])
    row["values"][key] = value
    with pytest.raises(ValueError):
        validate_response(row)


def test_stage_order_and_missing_batch(path):
    with pytest.raises(ValueError, match="Bronze"):
        transform_silver(path, "0" * 64)
    bronze = ingest_bronze(path, export_fixture())
    with pytest.raises(ValueError, match="Silver"):
        publish_gold(path, bronze["batch_id"])
    assert inspect_layers(path)["tables"]["gold_snapshots"] == 0


def test_api_only_accepts_fixed_synthetic_data(path):
    with TestClient(
        create_app(path), headers={"X-API-TOKEN": DEMO_API_TOKEN}
    ) as client:
        export_id = client.post("/mock-qualtrics/exports").json()["export_id"]
        assert (
            client.get(f"/mock-qualtrics/exports/{export_id}").json()["status"]
            == "complete"
        )
        assert client.get("/mock-qualtrics/exports/arbitrary").status_code == 404
        payload = client.get(f"/mock-qualtrics/exports/{export_id}/file").json()
        bad = deepcopy(payload)
        bad["responses"][0]["employee_email"] = "not-permitted@example.invalid"
        assert client.post("/layers/bronze", json=bad).status_code == 409
        assert client.get("/layers").json()["tables"]["bronze_batches"] == 0
        bronze = client.post("/layers/bronze", json=payload).json()
        assert (
            client.post(
                "/layers/gold", json={"batch_id": bronze["batch_id"]}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/layers/silver", json={"batch_id": bronze["batch_id"]}
            ).status_code
            == 200
        )
        gold = client.post("/layers/gold", json={"batch_id": bronze["batch_id"]}).json()
        assert gold["status"] == "ready" and gold["metrics"]["enps"]["value"] == 22.22
        assert (
            client.post("/layers/gold", json={"batch_id": "../other"}).status_code
            == 422
        )


def test_invalid_latest_does_not_restore_old_valid_answer(path):
    bronze = ingest_bronze(path, export_fixture())
    # Test corruption at the storage boundary without allowing custom HTTP payloads.
    with connect(path) as db:
        record = export_fixture()["responses"][0]
        record["values"].update(recordedDate="2026-10-21T09:00:00Z", Q_ENGAGEMENT=99)
        db.execute(
            "INSERT INTO bronze_responses VALUES (?, ?, ?, ?)",
            (
                bronze["batch_id"],
                "new-invalid-version",
                record["responseId"],
                json.dumps(record),
            ),
        )
    result = transform_silver(path, bronze["batch_id"])
    assert result["accepted_responses"] == 11 and result["quarantined_responses"] == 2
    with connect(path) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM silver_responses WHERE response_id='R_SYNTH_001'"
            ).fetchone()[0]
            == 0
        )
