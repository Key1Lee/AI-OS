import pytest
from fastapi.testclient import TestClient

from data_system_map.demo import load_artifacts
from data_system_map.api.main import create_app
from data_system_map.config import Settings


@pytest.fixture
def artifacts():
    return load_artifacts()


@pytest.fixture
def map_client(tmp_path):
    def factory():
        app = create_app(Settings(database_path=tmp_path/'metadata.db'))
        client = TestClient(app)
        client.headers['X-Observability-Token'] = client.get('/api/config').json()['request_token']
        return client, app
    return factory
