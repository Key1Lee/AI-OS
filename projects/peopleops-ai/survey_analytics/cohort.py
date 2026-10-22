"""Reproducible fictional survey population; no actual Samsara data or staffing."""

import json
import random
from functools import lru_cache

SURVEY_ID = "SV_SYNTHETIC_SAMSARA_5000"
DEPARTMENTS = {
    "Engineering": 1200,
    "Sales": 1000,
    "Customer Success": 700,
    "Operations": 600,
    "Support": 450,
    "Product": 300,
    "Marketing": 250,
    "Finance": 200,
    "People": 180,
    "IT": 120,
}


@lru_cache(maxsize=1)
def _cohort_json():
    """Generate one seeded survey row per fictional employee, including skipped questions."""
    rng = random.Random(20261021)
    responses = []
    for department_index, (department, count) in enumerate(DEPARTMENTS.items()):
        mean = [4.05, 3.65, 3.95, 3.45, 3.55, 4.2, 3.85, 4.0, 4.15, 3.8][
            department_index
        ]
        for _ in range(count):
            number = len(responses) + 1
            engagement = max(1, min(5, round(rng.gauss(mean, 0.9))))
            csat = max(1, min(5, round(rng.gauss(mean + 0.1, 0.85))))
            enps = max(0, min(10, round(rng.gauss(mean * 2, 1.8))))
            responses.append(
                {
                    "responseId": f"R_SAM_SYNTH_{number:05d}",
                    "values": {
                        "employeeId": f"EMP_SYNTH_{number:05d}",
                        "recordedDate": "2026-10-21T08:00:00Z",
                        "finished": True,
                        "department": department,
                        "Q_ENGAGEMENT": None if number % 37 == 0 else engagement,
                        "Q_CSAT": None if number % 29 == 0 else csat,
                        "Q_ENPS": None if number % 41 == 0 else enps,
                        "durationSeconds": rng.randint(80, 720),
                    },
                }
            )
    return json.dumps(
        {
            "synthetic": True,
            "survey_id": SURVEY_ID,
            "cohort_id": "fictional-samsara-5000-oct-2026-v1",
            "invited_count": 5000,
            "department_roster": DEPARTMENTS,
            "responses": responses,
        }
    )


def cohort_fixture():
    """Return an independent copy of the fixed 5,000-employee export."""
    return json.loads(_cohort_json())
