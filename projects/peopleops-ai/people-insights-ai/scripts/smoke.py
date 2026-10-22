"""Exercise the running UI API and optional real n8n relay; record actual timings."""

import argparse
import csv
import io
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = [
    "Give me the Sales happiness report.",
    "Compare it with Research & Development.",
    "What about attrition?",
    "Can you download this report?",
    "Show me the Qualtrics engagement score.",
]


def demonstrate(client, base, mode):
    session = uuid4().hex
    results, timings = [], []
    for message in MESSAGES:
        start = perf_counter()
        response = client.post(
            base + "/api/chat/route",
            json={"session_id": session, "message": message},
            headers={"X-Execution-Mode": mode},
        )
        timings.append(round((perf_counter() - start) * 1000, 2))
        response.raise_for_status()
        results.append(response.json())
    a, b, c, d, e = results
    assert a["report"]["departments"][0]["employees"] == 446
    assert a["report"]["departments"][0]["metrics"]["job_satisfaction"]["value"] == 61.4
    assert (
        a["report"]["departments"][0]["metrics"]["work_life_balance"]["value"] == 73.5
    )
    assert len(b["report"]["departments"]) == 2
    assert (
        c["report"]["metrics"] == ["attrition"] and len(c["report"]["departments"]) == 2
    )
    assert c["report"]["report_id"] == d["report"]["report_id"]
    exported = client.get(base + d["report"]["csv_url"])
    exported.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows) == 2 and {row["percentage"] for row in rows} == {"20.6", "13.8"}
    assert "EmployeeNumber" not in exported.text
    assert e["status"] == "unsupported" and e["report"] is None
    (ROOT / "evidence" / f"{mode}-comparison.csv").write_text(exported.text)
    return {
        "mode": mode,
        "scenarios_passed": ["A", "B", "C", "D", "E"],
        "scenario_http_ms": timings,
        "responses": results,
    }


def benchmark(client, base, mode, count=20):
    timings = []
    for _ in range(count):
        start = perf_counter()
        response = client.post(
            base + "/api/chat/route",
            json={"session_id": uuid4().hex, "message": "Sales job satisfaction"},
            headers={"X-Execution-Mode": mode},
        )
        response.raise_for_status()
        assert response.json()["status"] == "report"
        timings.append((perf_counter() - start) * 1000)
    ordered = sorted(timings)
    return {
        "requests": count,
        "method": "sequential localhost HTTP round trips; includes configured relay",
        "p50_ms": round(statistics.median(timings), 2),
        "p95_ms": round(ordered[int(0.95 * count) - 1], 2),
        "max_ms": round(max(timings), 2),
        "samples_ms": [round(value, 2) for value in timings],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8813")
    parser.add_argument("--n8n", action="store_true")
    args = parser.parse_args()
    modes = ["direct", "n8n"] if args.n8n else ["direct"]
    evidence = {
        "status": "passed",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "synthetic": True,
        "demonstrations": [],
        "timing": {},
        "business_time_saved": "Not measured",
    }
    with httpx.Client(
        timeout=25, headers={"X-Demo-Key": "demo-hr-manager"}, trust_env=False
    ) as client:
        client.get(args.base + "/health").raise_for_status()
        for mode in modes:
            evidence["demonstrations"].append(demonstrate(client, args.base, mode))
            evidence["timing"][mode] = benchmark(client, args.base, mode)
        denied = client.post(
            args.base + "/api/report",
            json={"department": "Human Resources", "metrics": ["attrition"]},
            headers={"X-Demo-Key": "demo-sales-manager"},
        )
        assert denied.status_code == 403
        if args.n8n:
            failure = client.post(
                "http://127.0.0.1:5680/webhook/people-insights-chat",
                json={"session_id": "safe-error", "message": "Sales report"},
                headers={"X-Demo-Key": "invalid-demo-identity"},
            )
            failure.raise_for_status()
            assert (
                failure.json()["status"] == "error" and failure.json()["report"] is None
            )
            evidence["n8n_failure_branch"] = (
                "passed: backend unauthorized request returned safe workflow error"
            )
    (ROOT / "evidence/live-checks.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(
        json.dumps(
            {key: value for key, value in evidence.items() if key != "demonstrations"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
