"""Generate fictional records only; no employee identities or network calls."""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Illustrative software-company allocation, not actual Samsara staffing.
DEPARTMENTS = {
    "Human Resources": 250,
    "Marketing": 500,
    "Engineering & Product": 2000,
    "Sales": 1250,
    "Customer Success & Support": 1000,
}


def seed():
    records, headcount = [], []
    for year in (2024, 2025, 2026):
        for d, (department, eligible) in enumerate(DEPARTMENTS.items()):
            rng = random.Random(year * 100 + d)
            headcount.append({"SurveyYear": year, "Department": department, "EligibleEmployees": eligible})
            completion_rate = [.82, .75, .78, .74, .80][d] + [0, .015, -.01][year - 2024]
            completed = round(eligible * completion_rate)
            incomplete = round(eligible * .04)
            missing = max(1, round(completed * .018))
            invalid = max(1, round(completed * .005))
            duplicates = max(2, round(completed * .01))
            max_day = 293 if year == 2026 else (365 if year == 2024 else 364)
            for i in range(completed + incomplete):
                date = datetime(year, 1, 1, 9, tzinfo=timezone.utc) + timedelta(days=rng.randrange(max_day + 1))
                # Correlated answers share a respondent baseline, with question-level noise.
                center = 3.25 + (year - 2024) * .23 + [.12, -.08, .18, -.12, -.02][d]
                respondent = rng.gauss(center, .65)
                scores = [min(5, max(1, round(rng.gauss(respondent + offset, .48)))) for offset in (.08, -.10, .02)]
                record = {
                    "ResponseID": f"R_DEMO_{year}_{d}_{i:04d}",
                    "RecordedDate": date.isoformat().replace("+00:00", "Z"),
                    "SurveyYear": year, "Department": department,
                    "Finished": 1 if i < completed else 0,
                    **dict(zip(("QID1", "QID2", "QID3"), scores)),
                }
                if i < missing:
                    record["QID2"] = None
                if missing <= i < missing + invalid:
                    record["QID3"] = 6
                records.append(record)
                if missing + invalid <= i < missing + invalid + duplicates:
                    updated = dict(record)
                    updated["RecordedDate"] = (date + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
                    updated["QID1"] = min(5, scores[0] + 1)
                    # Latest invalid revision must supersede an earlier valid response.
                    if i == missing + invalid + 1:
                        updated["QID3"] = None
                    records.append(updated)
    rng = random.Random(61021)
    rng.shuffle(records)
    for name, data in (("qualtrics_responses.json", records), ("eligible_headcount.json", headcount)):
        (ROOT / "fixtures" / name).write_text(json.dumps(data, indent=2) + "\n")
    print(f"Seeded {len(records)} synthetic submissions; {len(headcount)} eligible cohorts.")


if __name__ == "__main__":
    seed()
