"""One local FastAPI process serves chat, aggregate reports, exports and the UI."""

import os
from collections import OrderedDict
from time import monotonic, perf_counter
from typing import Annotated
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .analytics import METRICS, build_report, report_csv
from .chatbot import SessionStore, handle_chat
from .data_loader import ROOT, load_data
from .models import (
    DEPARTMENTS,
    ChatRequest,
    ChatResult,
    QualtricsImport,
    ReportRequest,
    ReportResponse,
)
from .qualtrics import parse_qualtrics, provided_report

load_dotenv(ROOT / ".env")
# These deliberately public demo identities are not production authentication.
IDENTITIES = {
    "demo-hr-manager": {
        "id": "hr-manager",
        "departments": list(DEPARTMENTS),
        "admin": False,
    },
    "demo-sales-manager": {
        "id": "sales-manager",
        "departments": ["Sales"],
        "admin": False,
    },
    "demo-admin": {"id": "demo-admin", "departments": list(DEPARTMENTS), "admin": True},
}


def principal(x_demo_key: str = Header(default="")):
    """Resolve a fixed server-side demo identity; request roles never authorize access."""
    if x_demo_key not in IDENTITIES:
        raise HTTPException(401, "Use a documented local demo identity")
    return IDENTITIES[x_demo_key]


Owner = Annotated[dict, Depends(principal)]


def create_app(data=None, data_error=None):
    """Create an isolated app with its own CSV snapshot, sessions and aggregate reports."""
    api = FastAPI(title="People Insights AI", version="1.0.0")
    if data is None and data_error is None:
        try:
            data = load_data()
        except ValueError as error:
            data_error = str(error)
    api.state.data = data
    api.state.data_error = data_error
    api.state.sessions = SessionStore()
    api.state.reports = OrderedDict()
    api.state.qualtrics = None

    def ready():
        if api.state.data_error or api.state.data is None:
            raise HTTPException(503, api.state.data_error or "Dataset unavailable")

    def save_report(owner, departments, metrics, source):
        if any(department not in owner["departments"] for department in departments):
            raise HTTPException(403, "Department access denied")
        if source == "ibm":
            ready()
            result = build_report(api.state.data, departments, metrics)
        else:
            if api.state.qualtrics is None:
                raise ValueError("Qualtrics data is not connected")
            result = provided_report(api.state.qualtrics, departments, metrics)
        report_id = uuid4().hex
        result["report_id"] = report_id
        result["csv_url"] = f"/api/reports/{report_id}/csv"
        now = monotonic()
        for key in list(api.state.reports):
            if now - api.state.reports[key]["created"] > 1800:
                del api.state.reports[key]
        if len(api.state.reports) >= 256:
            api.state.reports.popitem(last=False)
        api.state.reports[report_id] = {
            "owner": owner["id"],
            "created": now,
            "report": result,
        }
        return result

    @api.exception_handler(ValueError)
    async def invalid_value(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @api.get("/health")
    def health():
        return JSONResponse(
            status_code=503 if api.state.data_error else 200,
            content={
                "status": "unavailable" if api.state.data_error else "ok",
                "synthetic_only": True,
                "dataset_rows": 0 if data is None else len(data),
                "detail": api.state.data_error,
            },
        )

    @api.get("/api/departments")
    def departments(owner: Owner):
        return {"departments": owner["departments"], "identity": owner["id"]}

    @api.get("/api/metrics")
    def metrics(owner: Owner):
        return {"metrics": METRICS, "minimum_group_size": 5}

    @api.get("/api/sources")
    def sources(owner: Owner):
        return {
            "ibm": {
                "label": "IBM HR Analytics synthetic sample",
                "available": api.state.data_error is None,
                "rows": 0 if data is None else len(data),
            },
            "qualtrics": {
                "available": api.state.qualtrics is not None,
                "label": "Synthetic provided aggregates",
            },
        }

    @api.post("/api/report", response_model=ReportResponse)
    def report(body: ReportRequest, owner: Owner):
        started = perf_counter()
        with api.state.sessions.lock:
            result = save_report(
                owner,
                body.selected_departments(),
                list(dict.fromkeys(body.metrics)),
                body.source,
            )
        return {
            "status": "report",
            "report": result,
            "elapsed_ms": round((perf_counter() - started) * 1000, 2),
        }

    @api.post("/api/chat", response_model=ChatResult)
    def chat(body: ChatRequest, owner: Owner):
        started = perf_counter()
        with api.state.sessions.lock:
            state = api.state.sessions.get(owner["id"], body.session_id)
            result = handle_chat(
                body.message,
                state,
                owner["departments"],
                lambda departments, metrics, source: save_report(
                    owner, departments, metrics, source
                ),
                api.state.qualtrics is not None,
            )
            result["context"] = {
                "departments": state["departments"],
                "metrics": state["metrics"],
                "source": state["source"],
            }
        result["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
        return result

    @api.get("/api/reports/{report_id}/csv")
    def download(report_id: str, owner: Owner):
        stored = api.state.reports.get(report_id)
        if (
            stored is None
            or stored["owner"] != owner["id"]
            or monotonic() - stored["created"] > 1800
        ):
            raise HTTPException(404, "Report not found or expired; generate it again")
        return Response(
            report_csv(stored["report"]),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="people-insights-report.csv"',
                "Cache-Control": "no-store",
            },
        )

    @api.post("/api/admin/qualtrics")
    def import_scores(body: QualtricsImport, owner: Owner):
        if not owner["admin"]:
            raise HTTPException(403, "Demo administrator access required")
        parsed = parse_qualtrics(body.csv_text)
        with api.state.sessions.lock:
            api.state.qualtrics = parsed
        return {
            "status": "imported",
            "source": "qualtrics",
            "synthetic": True,
            "rows": len(parsed["rows"]),
            "survey_name": parsed["name"],
            "survey_period": parsed["period"],
            "note": "Provided scores, not recomputed. Replaces the previous in-memory import.",
        }

    @api.post("/api/chat/route", response_model=ChatResult)
    async def route_chat(
        body: ChatRequest,
        owner: Owner,
        x_demo_key: str = Header(default=""),
        x_execution_mode: str = Header(default="direct"),
    ):
        """Relay to a fixed configured n8n webhook or use the exact same direct handler."""
        if x_execution_mode not in ("direct", "n8n"):
            raise HTTPException(422, "Execution mode must be direct or n8n")
        if x_execution_mode == "direct":
            return {**chat(body, owner), "execution_mode": "direct"}
        url = os.getenv(
            "N8N_WEBHOOK_URL", "http://127.0.0.1:5680/webhook/people-insights-chat"
        )
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                response = await client.post(
                    url, json=body.model_dump(), headers={"X-Demo-Key": x_demo_key}
                )
                response.raise_for_status()
                result = response.json()
                if result.get("status") not in (
                    "report",
                    "clarification",
                    "unsupported",
                    "error",
                ):
                    raise ValueError("Invalid workflow result")
                ChatResult.model_validate(result)
            return {**result, "execution_mode": "n8n"}
        except (httpx.HTTPError, ValueError):
            # Do not automatically replay a stateful chat after a timeout.
            raise HTTPException(
                502,
                "n8n is unavailable or returned an invalid response. Switch to Direct API. If the request timed out, start a new conversation to avoid replaying an uncertain turn.",
            )

    @api.get("/")
    def index():
        return FileResponse(ROOT / "frontend/index.html")

    api.mount("/assets", StaticFiles(directory=ROOT / "frontend"), name="assets")
    return api


app = create_app()
