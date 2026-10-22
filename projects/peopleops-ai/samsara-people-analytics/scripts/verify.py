"""Independent standard-library reference. Never imports or invokes TypeScript.

Generate with --write; without it, independently reconcile the committed golden.
"""
import argparse
import hashlib
import itertools
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEARS = [2024, 2025, 2026]
DEPARTMENTS = ["Human Resources", "Marketing", "Engineering & Product", "Sales", "Customer Success & Support"]


def checksum(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def reference(snapshot, years, departments):
    # Stable tie rule: later source position wins if timestamps are identical.
    latest = {}
    for position, row in enumerate(snapshot["responses"]):
        key = row["ResponseID"]
        stamp = datetime.fromisoformat(row["RecordedDate"].replace("Z", "+00:00"))
        if key not in latest or (stamp, position) >= latest[key][:2]:
            latest[key] = (stamp, position, row)
    valid = []
    for stamp, _, row in latest.values():
        scores = [row.get(q) for q in ("QID1", "QID2", "QID3")]
        if (type(row.get("Finished")) is int and row["Finished"] == 1
                and row["Department"] in DEPARTMENTS and row["SurveyYear"] in YEARS
                and stamp.year == row["SurveyYear"]
                and stamp.isoformat()[:10] <= ("2026-10-21" if stamp.year == 2026 else f"{stamp.year}-12-31")
                and all(type(s) is int and 1 <= s <= 5 for s in scores)):
            valid.append((row, (sum(scores) / 3 - 1) * 25))

    def aggregate(year, selected):
        values = [score for row, score in valid if row["SurveyYear"] == year and row["Department"] in selected]
        eligible = sum(r["EligibleEmployees"] for r in snapshot["headcount"] if r["SurveyYear"] == year and r["Department"] in selected)
        return {"year": year, "score": sum(values) / len(values) if values else None,
                "validRespondents": len(values), "eligibleEmployees": eligible,
                "responseRate": len(values) / eligible * 100 if eligible else None}

    annual = []
    for year in years:
        row = aggregate(year, departments)
        previous = aggregate(year - 1, departments)["score"]
        row["yoyChange"] = row["score"] - previous if row["score"] is not None and previous is not None else None
        annual.append(row)
    values = [score for row, score in valid if row["SurveyYear"] in years and row["Department"] in departments]
    eligible = sum(row["eligibleEmployees"] for row in annual)
    return {
        "annual": annual,
        "trend": {"fromYear": years[0], "toYear": years[-1], "change": annual[-1]["score"] - annual[0]["score"] if annual[-1]["score"] is not None and annual[0]["score"] is not None else None},
        "departments": [{**aggregate(year, [department]), "department": department} for year in years for department in departments],
        "overall": {"score": sum(values) / len(values) if values else None,
                    "validRespondents": len(values), "eligibleEmployees": eligible,
                    "responseRate": len(values) / eligible * 100 if eligible else None},
        "quality": {"retrievedRecords": len(snapshot["responses"]), "deduplicatedRecords": len(latest),
                    "duplicatesRemoved": len(snapshot["responses"]) - len(latest),
                    "invalidExcluded": len(latest) - len(valid), "validRecordsUsed": len(values)},
    }


def subsets(items):
    return [list(c) for size in range(1, len(items) + 1) for c in itertools.combinations(items, size)]


def key(years, departments):
    return ",".join(map(str, sorted(years))) + "|" + ",".join(sorted(departments))


def build():
    snapshot = {"responses": json.loads((ROOT / "fixtures/qualtrics_responses.json").read_text()),
                "headcount": json.loads((ROOT / "fixtures/eligible_headcount.json").read_text())}
    return {"schemaVersion": 1, "sourceChecksum": checksum(snapshot), "reference": "Independent Python standard library",
            "reports": {key(ys, ds): reference(snapshot, ys, ds) for ys in subsets(YEARS) for ds in subsets(DEPARTMENTS)}}


def close(a, b):
    if type(a) is not type(b) and not (type(a) in (int, float) and type(b) in (int, float)):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if type(a) in (int, float):
        return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-9
    return a == b


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = build()
    target = ROOT / "fixtures/golden_report.json"
    if args.write:
        target.write_text(json.dumps(expected, indent=2) + "\n")
        print(f"Wrote independent reference for {len(expected['reports'])} filter combinations.")
    else:
        assert close(expected, json.loads(target.read_text())), "Golden reference differs from independent recalculation"
        print(f"PASS: all {len(expected['reports'])} reference combinations; checksum {expected['sourceChecksum']}")
