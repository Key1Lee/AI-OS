from copy import deepcopy
from datetime import date
import pytest
from exercises.e01_cleaning import normalize_employee


def test_normalizes_actual_maya_record(fixture_data):
    row = fixture_data["raw_employees"][0]
    result = normalize_employee(row)
    assert result.full_name == "Maya Chen"
    assert result.email == "person001@example.test"
    assert result.status == "active"
    assert result.hire_date == date.fromisoformat(row["hire_date"])
    assert result.pto_hours == 80


def test_preserves_source(fixture_data):
    row = fixture_data["raw_employees"][0]
    original = deepcopy(row)
    normalize_employee(row)
    assert row == original


@pytest.mark.parametrize("change", [{"email": None}, {"hire_date": "not-a-date"}, {"pto_hours": -8},
                                   {"status": "unknown"}, {"source_updated_at": "2026-10-01T08:00:00"}])
def test_rejects_invalid_values(fixture_data, change):
    with pytest.raises(ValueError):
        normalize_employee(dict(fixture_data["raw_employees"][0], **change))


def test_nullable_manager_and_departure(fixture_data):
    result = normalize_employee(fixture_data["raw_employees"][0])
    assert result.manager_id is None and result.termination_date is None
