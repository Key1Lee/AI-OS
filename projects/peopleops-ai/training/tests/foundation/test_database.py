import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from lab import models as m
from lab.embeddings import embed

pytestmark = pytest.mark.database


def test_real_postgres_counts_and_vector_roundtrip(db_session):
    assert db_session.scalar(select(func.count()).select_from(m.Employee)) == 120
    assert db_session.scalar(select(func.count()).select_from(m.RecruitingEvent)) == 240
    assert db_session.scalar(select(func.count()).select_from(m.Policy)) == 16
    assert db_session.scalar(select(func.count()).select_from(m.Ticket)) == 60
    chunk = db_session.get(m.PolicyChunk, "PTO:2:1:0")
    distance = db_session.scalar(select(m.PolicyChunk.embedding.cosine_distance(embed(chunk.body))).where(m.PolicyChunk.chunk_id == chunk.chunk_id))
    assert abs(distance) < 1e-5
    assert db_session.scalar(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))


def test_database_rejects_orphan_ticket(db_session):
    from datetime import datetime, timezone
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(m.Ticket(ticket_id="TEST-ORPHAN", employee_id="MISSING", category="Payroll", subject="test", status="open", created_at=datetime.now(timezone.utc)))
        db_session.flush()


def test_database_rejects_duplicate_employee_email(db_session):
    from lab.bootstrap import typed
    from lab.fixtures import load
    row = dict(load()["employees"][0], employee_id="EMP-999")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(m.Employee(**typed(row)))
        db_session.flush()
