import json
import pytest
from fastapi.testclient import TestClient
from peopleops.app import create_app
from peopleops.config import Settings
from peopleops.seed import bootstrap


@pytest.fixture
def settings(tmp_path):
    settings = Settings(data_dir=tmp_path, retry_delay=0)
    bootstrap(settings)
    return settings


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def auth(settings):
    identities = json.loads((settings.data_dir / "demo-identities.json").read_text())
    return {item["principal_id"]: {"Authorization": f"Bearer {item['token']}"} for item in identities}
