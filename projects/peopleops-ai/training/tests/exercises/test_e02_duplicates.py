from copy import deepcopy
from exercises.e02_duplicates import latest_events


def test_older_delivery_does_not_replace_newer(fixture_data):
    result = latest_events(fixture_data["raw_recruiting_events"])
    assert len(result) == 240
    assert result[0]["event_id"] == "EVT-0001" and result[0]["stage"] == "applied"


def test_equal_version_last_input_wins_and_input_preserved(fixture_data):
    row = fixture_data["recruiting_events"][0]
    rows = [dict(row), dict(row, stage="offer")]
    original = deepcopy(rows)
    assert latest_events(rows) == [original[-1]]
    assert rows == original


def test_empty_batch():
    assert latest_events([]) == []
