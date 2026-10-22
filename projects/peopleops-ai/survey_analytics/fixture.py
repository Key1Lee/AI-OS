"""Fixed, non-personal survey answers; these are not from a Qualtrics account."""

from copy import deepcopy


def export_fixture():
    """Return a fresh synthetic export with duplicates, a revision, and bad data."""
    engagement = [5, 4, 4, 3, 5, 2, 4, 5, 3, 4]
    csat = [5, 4, 4, 3, 5, None, 4, 5, 3, 4]
    recommendation = [10, 9, 8, 7, 10, 6, 9, 8, 5, None]
    rows = []
    for i in range(12):
        complete = i < 10
        rows.append(
            {
                "responseId": f"R_SYNTH_{i + 1:03d}",
                "values": {
                    "recordedDate": "2026-10-20T09:00:00Z",
                    "finished": complete,
                    "department": "Engineering"
                    if i < 6
                    else "People"
                    if i < 10
                    else "Sales",
                    "Q_ENGAGEMENT": engagement[i] if complete else None,
                    "Q_CSAT": csat[i] if complete else None,
                    "Q_ENPS": recommendation[i] if complete else None,
                    "durationSeconds": 60 + i * 30,
                },
            }
        )
    rows.append(deepcopy(rows[0]))
    older = deepcopy(rows[1])
    older["values"].update(recordedDate="2026-10-19T09:00:00Z", Q_ENGAGEMENT=1)
    rows.append(older)
    invalid = deepcopy(rows[0])
    invalid["responseId"] = "R_SYNTH_BAD"
    invalid["values"]["Q_ENGAGEMENT"] = 9
    rows.append(invalid)
    return {
        "synthetic": True,
        "survey_id": "SV_SYNTHETIC_PULSE_OCT_2026",
        "cohort_id": "closed-cohort-2026-10",
        "invited_count": 20,
        "responses": rows,
    }
