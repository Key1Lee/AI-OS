import httpx
import pytest
from exercises.e11_reliability import fetch_all


def test_retries_only_failed_page():
    calls, sleeps = [], []
    def page(cursor, attempt):
        calls.append((cursor, attempt))
        if cursor == 2 and attempt < 3:
            raise httpx.ReadTimeout("injected")
        return {"items": [{"id": cursor}], "next_cursor": 2 if cursor == 0 else None, "schema_version": 1}
    assert fetch_all(page, sleeps.append) == [{"id": 0}, {"id": 2}]
    assert calls == [(0,1), (2,1), (2,2), (2,3)]
    assert sleeps == [0.1, 0.2]


def test_outage_has_bounded_attempts():
    calls = []
    def page(cursor, attempt):
        calls.append(attempt)
        raise httpx.ReadTimeout("injected")
    with pytest.raises(httpx.ReadTimeout):
        fetch_all(page, lambda _: None)
    assert calls == [1,2,3]


@pytest.mark.parametrize("page", [{"items": [], "next_cursor": 0, "schema_version": 1}, {"items": [], "next_cursor": None, "schema_version": 2}, {"items": "invalid", "next_cursor": None}])
def test_rejects_cycles_and_bad_contracts(page):
    with pytest.raises(ValueError):
        fetch_all(lambda **_: page, lambda _: None)
