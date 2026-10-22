import os
import pytest
from fastapi.testclient import TestClient
from lab.api import create_app
from lab.db import make_engine
from lab.bootstrap import bootstrap
from lab.fixtures import load


@pytest.fixture
def fixture_data():
    return load()


@pytest.fixture
def client():
    with TestClient(create_app()) as value:
        yield value


@pytest.fixture
def auth(client):
    identities = client.get("/lab/identities").json()
    return {i["role"]: {"Authorization": "Bearer " + i["token"]} for i in identities}


@pytest.fixture
def db_session():
    if os.environ.get("LAB_DATABASE_TESTS") != "1":
        pytest.skip("Start training DB; set LAB_DATABASE_TESTS=1 to run PostgreSQL checks")
    from sqlalchemy.orm import Session
    engine = make_engine()
    if engine.url.database != "peopleops_training":
        pytest.fail("Database tests only permit the dedicated peopleops_training database")
    bootstrap(engine)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()
    engine.dispose()
