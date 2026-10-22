"""Generate fictional records only; no employee identities or network calls."""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPARTMENTS = ["Engineering", "Sales", "Customer Support"]


def seed():
    records, headcount = [], []
    for year in (2024, 2025, 2026):
        for d, department in enumerate(DEPARTMENTS):
            rng = random.Random(year * 100 + d)
            headcount.append({"SurveyYear": year, "Department": department, "EligibleEmployees": 60})
            completed = 44 + (year + d * 2) % 5
            max_day = 293 if year == 2026 else (365 if year == 2024 else 364)
            for i in range(completed + 7):
                date = datetime(year, 1, 1, 9, tzinfo=timezone.utc) + timedelta(days=rng.randrange(max_day + 1))
                center = 3.25 + (year - 2024) * .23 + [.18, -.12, -.02][d]
                scores = [min(5, max(1, round(rng.gauss(center, .83)))) for _ in range(3)]
                record = {
                    "ResponseID": f"R_DEMO_{year}_{d}_{i:03d}",
                    "RecordedDate": date.isoformat().replace("+00:00", "Z"),
                    "SurveyYear": year, "Department": department,
                    "Finished": 1 if i < completed + 3 else 0,
                    **dict(zip(("QID1", "QID2", "QID3"), scores)),
                }
                if i in (completed, completed + 1):
                    record["QID2"] = None
                if i == completed + 2:
                    record["QID3"] = 6
                records.append(record)
                if i in (0, 1):
                    updated = dict(record)
                    updated["RecordedDate"] = (date + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
                    updated["QID1"] = min(5, scores[0] + 1)
                    # Latest invalid revision must supersede an earlier valid response.
                    if i == 1:
                        updated["QID3"] = None
                    records.append(updated)
    rng = random.Random(61021)
    rng.shuffle(records)
    for name, data in (("qualtrics_responses.json", records), ("eligible_headcount.json", headcount)):
        (ROOT / "fixtures" / name).write_text(json.dumps(data, indent=2) + "\n")
    print(f"Seeded {len(records)} synthetic submissions; {len(headcount)} eligible cohorts.")


if __name__ == "__main__":
    seed()
