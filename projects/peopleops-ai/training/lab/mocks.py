"""Unsafe-to-publish synthetic source server. Never an employee authorization API."""
import asyncio
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from lab.contracts import Health, Page
from lab.fixtures import load

Scenario = Literal["normal", "timeout", "intermittent", "unavailable", "missing", "duplicate", "schema_drift", "malformed"]
RESOURCES = {"workday": "raw_employees", "jobs": "jobs", "candidates": "candidates", "greenhouse": "raw_recruiting_events",
             "policies": "policies", "tickets": "tickets", "slack": "slack_messages"}


def create_mock_app():
    app = FastAPI(title="PeopleOps synthetic enterprise sources")
    data = load()

    @app.get("/health", response_model=Health)
    def health():
        return Health(status="ok")

    @app.get("/mock/{source}", response_model=Page)
    async def source_page(source: str, cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                          scenario: Scenario = "normal", attempt: int = Query(1, ge=1, le=10)):
        if source not in RESOURCES:
            raise HTTPException(404, "Unknown mock source")
        if scenario == "timeout":
            await asyncio.sleep(1.5)  # client timeout=0.2s demonstrates a real socket timeout
        if scenario == "unavailable" or (scenario == "intermittent" and attempt < 3):
            raise HTTPException(503, "Injected mock outage", headers={"Retry-After": "1"})
        rows = [dict(row) for row in data[RESOURCES[source]]]
        if scenario == "missing":
            rows = rows[1:]
        if scenario == "duplicate" and rows:
            rows.append(dict(rows[0]))
        if scenario == "schema_drift" and rows:
            rows[0]["unexpected_v2_field"] = "new contract"
            if "employee_id" in rows[0]:
                rows[0]["worker_id"] = rows[0].pop("employee_id")
        if scenario == "malformed" and rows:
            rows[0] = {"employee_id": ["invalid", "shape"], "email": None}
        return Page(items=rows[cursor:cursor + limit], next_cursor=cursor + limit if cursor + limit < len(rows) else None,
                    schema_version=2 if scenario == "schema_drift" else 1)

    return app


app = create_mock_app()
