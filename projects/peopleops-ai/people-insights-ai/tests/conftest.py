import pytest
from fastapi.testclient import TestClient

from app.data_loader import load_data
from app.main import create_app


@pytest.fixture(scope="session")
def data():
    return load_data()


@pytest.fixture
def client(data):
    with TestClient(create_app(data=data)) as client:
        client.headers["X-Demo-Key"] = "demo-hr-manager"
        yield client


def ask(client, message, session="test-session"):
    response = client.post(
        "/api/chat", json={"session_id": session, "message": message}
    )
    assert response.status_code == 200, response.text
    return response.json()
