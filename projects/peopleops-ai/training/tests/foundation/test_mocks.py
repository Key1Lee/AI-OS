import pytest
from fastapi.testclient import TestClient
from lab.mocks import create_mock_app, RESOURCES


@pytest.mark.parametrize("source", list(RESOURCES))
def test_paginated_source(source):
    client = TestClient(create_mock_app())
    cursor, records = 0, []
    while cursor is not None:
        response = client.get(f"/mock/{source}", params={"cursor": cursor, "limit": 17})
        assert response.status_code == 200
        data = response.json()
        records.extend(data["items"])
        cursor = data["next_cursor"]
    assert records


def test_faults_are_reproducible():
    client = TestClient(create_mock_app())
    for attempt, status in [(1, 503), (2, 503), (3, 200)]:
        assert client.get("/mock/workday", params={"scenario": "intermittent", "attempt": attempt}).status_code == status
    normal = client.get("/mock/workday").json()
    drift = client.get("/mock/workday?scenario=schema_drift").json()
    assert drift["schema_version"] == 2 and "worker_id" in drift["items"][0]
    assert client.get("/mock/workday?scenario=missing").json()["items"][0] != normal["items"][0]
    assert client.get("/mock/workday?scenario=malformed").json()["items"][0]["email"] is None
    assert client.get("/mock/workday?scenario=unavailable").status_code == 503
    assert client.get("/mock/unknown").status_code == 404
    assert client.get("/mock/workday?limit=101").status_code == 422
