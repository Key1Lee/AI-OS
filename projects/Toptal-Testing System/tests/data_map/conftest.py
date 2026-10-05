
import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from trainer.config import ROOT, Settings


@pytest.fixture
def artifacts():
    from data_system_map.demo import load_artifacts
    return load_artifacts()


@pytest.fixture
def map_client(tmp_path):
    created=[]
    def factory(path=None):
        app=create_app(Settings(database_path=path or tmp_path/f'profile-{len(created)}.db'))
        client=TestClient(app)
        client.headers['X-Trainer-Token']=client.get('/api/config').json()['request_token']
        created.append(app)
        return client,app
    yield factory
    for app in created:
        app.state.store.engine.dispose()
