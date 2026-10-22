import pytest
from lab.models import Employee
from exercises.e12_ingestion import ingest_employees

pytestmark = pytest.mark.database


def test_replay_is_unchanged(db_session, fixture_data):
    assert ingest_employees(fixture_data["employees"][:2], db_session) == {"inserted": 0, "updated": 0, "unchanged": 2}


def test_older_source_cannot_overwrite(db_session, fixture_data):
    row = dict(fixture_data["employees"][0], pto_hours=0, source_updated_at="2026-09-01T08:00:00+00:00")
    ingest_employees([row], db_session)
    assert db_session.get(Employee, "EMP-001").pto_hours == 80


def test_invalid_batch_does_not_partially_update(db_session, fixture_data):
    row = dict(fixture_data["employees"][0], pto_hours=88, source_updated_at="2026-10-02T08:00:00+00:00")
    with pytest.raises(ValueError):
        ingest_employees([row, {"employee_id": "BROKEN"}], db_session)
    db_session.expire_all()
    assert db_session.get(Employee, "EMP-001").pto_hours == 80
