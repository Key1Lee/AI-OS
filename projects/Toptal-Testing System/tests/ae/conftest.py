from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from trainer.config import ROOT, Settings
from trainer.exercises.bank import Bank


@pytest.fixture(scope="session")
def bank():
    return Bank(ROOT)


@pytest.fixture
def ae_factory(tmp_path):
    created = []

    def factory(*,path=None,runner=None,clock=None):
        settings=Settings(database_path=path or tmp_path/f"ae-{len(created)}.db")
        application=create_app(settings,runner=runner,clock=clock)
        client=TestClient(application)
        client.headers["X-Trainer-Token"]=client.get("/api/config").json()["request_token"]
        created.append(application)
        return client,application.state.service

    yield factory
    for application in created:
        application.state.store.engine.dispose()
