from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from lab.config import Settings


def make_engine(url: str | None = None):
    return create_engine(url or Settings().database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
