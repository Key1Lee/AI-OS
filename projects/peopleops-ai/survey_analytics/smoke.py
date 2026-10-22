"""Check real n8n HTTP execution and durable Gold output without a paid service."""

import json
from pathlib import Path
from urllib.request import Request, urlopen


def request(url, payload=None):
    """Send one local HTTP request and decode its JSON response."""
    data = json.dumps(payload).encode() if payload is not None else None
    with urlopen(
        Request(url, data=data, headers={"Content-Type": "application/json"}),
        timeout=120,
    ) as response:
        return json.load(response)


def main():
    """Execute the published workflow twice and verify stable results and row counts."""
    base = "http://127.0.0.1:8812"
    webhook = "http://127.0.0.1:5680/webhook/qualtrics-gold-test"
    assert request(base + "/health")["synthetic_only"]
    first = request(webhook, {})
    before = request(base + "/layers?batch_id=" + first["batch_id"])
    replay = request(webhook, {})
    after = request(base + "/layers?batch_id=" + first["batch_id"])
    assert first["status"] == replay["status"] == "ready"
    assert first["synthetic"] and replay["replayed"]
    assert {**first, "replayed": True} == replay
    assert before == after
    assert after["tables"] == {
        "bronze_batches": 1,
        "bronze_responses": 14,
        "silver_responses": 12,
        "quarantine": 1,
        "gold_snapshots": 1,
    }
    expected = {
        "response_rate": 50,
        "completion_rate": 83.33,
        "engagement_mean": 3.9,
        "engagement_favorable": 70,
        "csat_top_two_box": 77.78,
        "enps": 22.22,
    }
    assert {k: first["metrics"][k]["value"] for k in expected} == expected
    assert first["metrics"]["median_completion_seconds"] == 195
    assert first["department_breakdown"] == []
    assert first["privacy"]["department_slices_suppressed"]
    result = {
        "status": "passed",
        "synthetic_only": True,
        "webhook": webhook,
        "checks": [
            "health",
            "published n8n workflow execution",
            "Gold status",
            "seven exact metric results",
            "durable layer row counts",
            "replay idempotency",
            "small department suppression",
        ],
        "tables": after["tables"],
        "gold": replay,
    }
    reports = Path(__file__).parent / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "live-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": len(result["checks"]),
                "tables": after["tables"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
