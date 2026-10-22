"""Verify the actual local n8n 5,000-employee collection and visualization path."""

import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from .cohort import DEPARTMENTS
from .mock_account import DEMO_API_TOKEN
from .smoke import request


def main():
    """Run the published workflow twice, reconcile all employees, and download its artifacts."""
    api = "http://127.0.0.1:8812"
    result = request("http://127.0.0.1:5680/webhook/samsara-survey-5000", {})
    assert (
        result["status"] == "ready"
        and result["employees"] == 5000
        and result["departments"] == 10
    )
    gold = request(api + "/analytics")
    batch = gold["batch_id"]
    before = request(api + "/layers?batch_id=" + batch)
    assert request("http://127.0.0.1:5680/webhook/samsara-survey-5000", {}) == result
    assert request(api + "/layers?batch_id=" + batch) == before
    assert before["tables"] == {
        "bronze_batches": 1,
        "bronze_responses": 5000,
        "silver_responses": 5000,
        "quarantine": 0,
        "gold_snapshots": 1,
    }
    with urlopen(
        Request(
            api + f"/mock-qualtrics/exports/{batch}/file",
            headers={"X-API-TOKEN": DEMO_API_TOKEN},
        ),
        timeout=15,
    ) as response:
        source = json.load(response)
    assert len({r["values"]["employeeId"] for r in source["responses"]}) == 5000
    assert {
        s["department"]: s["counts"]["completed"] for s in gold["department_breakdown"]
    } == DEPARTMENTS
    for department in gold["department_breakdown"]:
        rows = [
            r["values"]
            for r in source["responses"]
            if r["values"]["department"] == department["department"]
        ]
        eng = [r["Q_ENGAGEMENT"] for r in rows if r["Q_ENGAGEMENT"] is not None]
        sat = [r["Q_CSAT"] for r in rows if r["Q_CSAT"] is not None]
        recommendation = [r["Q_ENPS"] for r in rows if r["Q_ENPS"] is not None]
        metrics = department["metrics"]
        assert metrics["experience_score"]["value"] == round(
            sum(eng) * 20 / len(eng), 2
        )
        assert metrics["csat_top_two_box"]["value"] == round(
            sum(x >= 4 for x in sat) * 100 / len(sat), 2
        )
        assert metrics["enps"]["value"] == round(
            (sum(x >= 9 for x in recommendation) - sum(x <= 6 for x in recommendation))
            * 100
            / len(recommendation),
            2,
        )
    reports = Path(__file__).parent / "reports"
    for extension in ("html", "csv"):
        with urlopen(api + result["downloads"][extension], timeout=20) as response:
            contents = response.read().decode()
        assert "EMP_SYNTH_" not in contents and "R_SAM_SYNTH_" not in contents
        (reports / f"samsara-5000.{extension}").write_text(contents)
        if extension == "csv":
            rows = list(csv.DictReader(io.StringIO(contents)))
            assert (
                len(rows) == 10 and sum(int(row["responses"]) for row in rows) == 5000
            )
    report = {
        "status": "passed",
        "synthetic": True,
        "checks": [
            "real n8n collection and visualization",
            "5,000 distinct employee IDs",
            "all ten department totals",
            "independent per-department metric arithmetic",
            "replay without duplicate rows",
            "downloaded HTML and CSV",
            "aggregate-only artifacts",
        ],
        "tables": before["tables"],
        "counts": gold["counts"],
        "metrics": gold["metrics"],
        "batch_id": batch,
        "workflow_id": "samsaraSurvey5000",
    }
    (reports / "cohort-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
