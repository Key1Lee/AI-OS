"""Loopback-published test API: fixed synthetic exports and a public fake token."""

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from .cohort import cohort_fixture
from .final_report import render_final_report
from .fixture import export_fixture
from .mock_account import account_fixture, require_mock_token
from .notifications import list_notifications, record_failure
from .pipeline import (
    digest,
    ingest_bronze,
    inspect_layers,
    publish_gold,
    transform_silver,
)
from .visualization import get_cohort_gold, publish_visualization, render_dashboard


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: Literal["demo", "employees5000"] = "demo"


class WorkflowFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: Literal[
        "qualtricsGold01", "qualtricsGoldFailure01", "samsaraSurvey5000"
    ]
    execution_id: str = Field(pattern=r"^(?:[0-9]{1,24}|trigger)$")
    last_node: Literal[
        "Start mock Qualtrics export",
        "Check export ready",
        "Download synthetic responses",
        "BRONZE - preserve raw export",
        "SILVER - validate and deduplicate",
        "GOLD - publish survey metrics",
        "Return metrics to test application",
        "Test application webhook",
        "Intentional checklist failure",
        "trigger",
        "Build department visualization",
    ]


def create_app(db_path=None):
    """Connect a test API to one local database; tests supply temporary paths."""
    path = db_path or os.environ.get(
        "SURVEY_DB", str(Path(__file__).parent / "data/survey.sqlite3")
    )
    api = FastAPI(title="Synthetic Qualtrics → Gold lab")
    mock = APIRouter(
        prefix="/mock-qualtrics", dependencies=[Depends(require_mock_token)]
    )

    @api.exception_handler(ValueError)
    async def invalid_request(request, error):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=409, content={"detail": str(error)})

    @api.get("/health")
    def health():
        return {"status": "ok", "synthetic_only": True}

    @mock.get("/account")
    def mock_account():
        return account_fixture()

    @mock.post("/exports")
    def start_export(request: ExportRequest | None = None):
        payload = (
            cohort_fixture()
            if request and request.dataset == "employees5000"
            else export_fixture()
        )
        return {
            "export_id": digest(payload),
            "synthetic": True,
            "note": "Local fixed fixture is immediately ready; no real Qualtrics API call",
        }

    @mock.get("/exports/{export_id}")
    def export_status(export_id: str):
        if export_id not in {digest(export_fixture()), digest(cohort_fixture())}:
            raise HTTPException(404, "Unknown synthetic export")
        return {
            "export_id": export_id,
            "status": "complete",
            "percentComplete": 100,
            "synthetic": True,
        }

    @mock.get("/exports/{export_id}/file")
    def download_export(export_id: str):
        export_status(export_id)
        return (
            cohort_fixture()
            if export_id == digest(cohort_fixture())
            else export_fixture()
        )

    @api.post("/layers/bronze")
    def bronze(payload: dict):
        return ingest_bronze(path, payload)

    @api.post("/layers/silver")
    def silver(batch: Batch):
        return transform_silver(path, batch.batch_id)

    @api.post("/layers/gold")
    def gold(batch: Batch):
        return publish_gold(path, batch.batch_id)

    @api.get("/layers")
    def layers(batch_id: str | None = None):
        return inspect_layers(path, batch_id)

    @api.get("/analytics")
    def analytics():
        return get_cohort_gold(path)

    @api.post("/analytics/publish")
    def generate_visualization(batch: Batch):
        result = publish_visualization(path, batch.batch_id)
        return {key: value for key, value in result.items() if key != "files"}

    @api.get("/analytics/export/{batch_id}/{extension}")
    def download_visualization(batch_id: str, extension: Literal["html", "csv"]):
        if len(batch_id) != 64 or any(c not in "0123456789abcdef" for c in batch_id):
            raise HTTPException(422, "Invalid batch identifier")
        result = publish_visualization(path, batch_id)
        return FileResponse(
            result["files"][extension],
            filename=f"synthetic-samsara-departments.{extension}",
        )

    @api.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        return render_dashboard(get_cohort_gold(path, required=False))

    @api.get("/report", response_class=HTMLResponse)
    def final_report():
        return render_final_report(get_cohort_gold(path, required=False))

    @api.get("/guide", response_class=HTMLResponse)
    def hiring_manager_guide():
        return (
            Path(__file__).parent / "docs/manager-pack/hiring-manager-guide.html"
        ).read_text()

    @api.get("/guide/download/{filename}")
    def guide_download(
        filename: Literal[
            "BusinessRequirements.docx",
            "WorkflowRequirements.docx",
            "architecture.svg",
            "architecture.png",
            "requirements.csv",
        ],
    ):
        return FileResponse(
            Path(__file__).parent / "docs/manager-pack" / filename, filename=filename
        )

    @api.post("/analytics/run")
    async def run_cohort():
        async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
            try:
                response = await client.post(
                    "http://n8n:5678/webhook/samsara-survey-5000", json={}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as error:
                raise HTTPException(
                    502,
                    "Local n8n cohort workflow could not complete; inspect its execution",
                ) from error

    @api.post("/notifications/workflow-error")
    def workflow_error(event: WorkflowFailure):
        return record_failure(path, event)

    @api.get("/notifications")
    def notification_inbox():
        return list_notifications(path)

    @api.get("/", response_class=HTMLResponse)
    def home():
        return """<!doctype html><html><head><title>Survey Gold output</title>
        <style>body{font:16px system-ui;background:#101827;color:#e6edf6;max-width:1000px;margin:40px auto;padding:20px}
        a{color:#68d5c8}pre{white-space:pre-wrap;background:#182537;padding:24px;border-radius:16px}p{line-height:1.6}</style></head>
        <body><h1>Qualtrics test → Gold metrics</h1><p>Fixed synthetic survey data · local SQLite medallion layers</p>
        <p><a href='http://127.0.0.1:5680/workflow/qualtricsGold01'>Open the n8n orchestrator</a> ·
        <a href='/docs'>API contracts</a> · <a href='/layers'>Gold JSON & table counts</a> ·
        <a href='/notifications'>Local error notifications</a></p>
        <p>n8n → start mock export → check ready → download → Bronze → Silver → Gold → return metrics.</p>
        <p>Run the workflow in n8n, then refresh this page. All values below come from persisted layers.</p>
        <pre id='output'>Loading…</pre><script>fetch('/layers').then(r=>r.json()).then(x=>{
        document.getElementById('output').textContent=JSON.stringify(x,null,2)});</script></body></html>"""

    api.include_router(mock)
    return api


app = create_app()
