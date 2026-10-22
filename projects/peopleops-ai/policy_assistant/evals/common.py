import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cases(layer):
    return [json.loads(line) for line in (ROOT / "evals/datasets" / (layer + "_cases.jsonl")).read_text().splitlines() if line.strip()]


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}


def outcome(case_id, passed, **metrics):
    return {"id": case_id, "passed": bool(passed), **metrics}


def summarize(results):
    return {"passed": sum(row["passed"] for row in results), "total": len(results),
            "failed_case_ids": [row["id"] for row in results if not row["passed"]], "cases": results}
