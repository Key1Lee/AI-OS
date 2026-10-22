"""Load already-normalized fixtures. Does not solve source ingestion exercises."""
from datetime import date, datetime
from sqlalchemy import text
from lab import models as m
from lab.db import make_engine, session_factory
from lab.embeddings import embed
from lab.fixtures import load


def typed(row):
    result = dict(row)
    for key in ("hire_date", "termination_date", "opened_on", "effective_on", "due_on"):
        if result.get(key):
            result[key] = date.fromisoformat(result[key])
    for key in ("source_updated_at", "occurred_at", "created_at"):
        if result.get(key):
            result[key] = datetime.fromisoformat(result[key])
    return result


def bootstrap(engine):
    data = load()
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        m.Base.metadata.create_all(connection)
    with session_factory(engine).begin() as session:
        # A single bootstrap lock prevents concurrent first-start duplicate loads.
        session.execute(text("SELECT pg_advisory_xact_lock(82749301)"))
        if session.get(m.SeedMarker, data["metadata"]["version"]):
            return "preserved"
        for name, model in [("employees", m.Employee), ("jobs", m.Job), ("candidates", m.Candidate),
                            ("recruiting_events", m.RecruitingEvent), ("tickets", m.Ticket), ("onboarding_tasks", m.OnboardingTask)]:
            for row in data[name]:
                session.add(model(**typed(row)))
                if name == "employees" and row["manager_id"] is None:
                    session.flush()
            session.flush()
        for policy in data["policies"]:
            session.add(m.Policy(**typed({k: v for k, v in policy.items() if k != "sections"})))
            session.flush()
            for section in policy["sections"]:
                key = f"{policy['policy_id']}:{policy['version']}:{section['section_id']}"
                session.add(m.PolicySection(section_key=key, policy_id=policy["policy_id"], version=policy["version"], **section))
                session.flush()
                # Fixture sections are pre-authored chunks. E04 implements parsing arbitrary documents.
                session.add(m.PolicyChunk(chunk_id=key + ":0", section_key=key, body=section["body"], embedding=embed(section["body"])))
        session.add(m.SeedMarker(version=data["metadata"]["version"]))
    return "seeded"


if __name__ == "__main__":
    engine = make_engine()
    try:
        print(bootstrap(engine))
    finally:
        engine.dispose()
