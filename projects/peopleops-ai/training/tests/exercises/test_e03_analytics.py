from datetime import date
import pytest
from sqlalchemy import text
from lab.sql_queries import query

pytestmark = pytest.mark.database


def run(db, name):
    return db.execute(text(query(name)), {"as_of": date(2026,10,1), "period_start": date(2026,9,1)}).mappings().all()


def test_headcount(db_session):
    assert [dict(r) for r in run(db_session, "headcount")] == [
        {"department": "Engineering", "headcount": 30}, {"department": "Operations", "headcount": 30},
        {"department": "People", "headcount": 20}, {"department": "Sales", "headcount": 30}]


def test_turnover(db_session, fixture_data):
    result = run(db_session, "turnover")
    assert len(result) == 1
    assert result[0]["departures"] == 10
    # Opening headcount includes people employed on Sep 1; departure day is excluded.
    opening = sum(e["hire_date"] <= "2026-09-01" and (not e["termination_date"] or e["termination_date"] > "2026-09-01") for e in fixture_data["employees"])
    assert result[0]["opening_headcount"] == opening
    assert result[0]["closing_headcount"] == 110
    assert float(result[0]["turnover_rate"]) == pytest.approx(10 / ((opening + 110) / 2))


def test_funnel_does_not_multiply_candidates(db_session):
    assert {r["stage"]: r["candidates"] for r in run(db_session, "funnel")} == {"applied": 80, "screen": 80, "interview": 80}


def test_onboarding_denominator(db_session):
    result = run(db_session, "onboarding")
    assert len(result) == 4
    assert sum(r["assigned"] for r in result) == 60
    assert sum(r["completed"] for r in result) == 30
    for row in result:
        assert float(row["completion_rate"]) == pytest.approx(row["completed"] / row["assigned"])
