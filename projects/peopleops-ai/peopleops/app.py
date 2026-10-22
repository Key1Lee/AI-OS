"""FastAPI service: authentication, ownership, and permission checks live here."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
from time import perf_counter
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .analytics import freshness, metrics, operations
from .config import PACKAGE, Settings, utcnow
from .db import audit, connect, rows
from .integrations import SCENARIOS, source_records
from .pipeline import ingest
from .retrieval import answer_question, visible_policies
from .routing import route_request
from .seed import bootstrap
from .workflows import deliver, queue_reminders

bearer = HTTPBearer(auto_error=False)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TicketInput(Input):
    subject: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    employee_id: str | None = None
    priority: Literal["normal", "high"] = "normal"


class QuestionInput(Input):
    question: str = Field(min_length=3, max_length=500)


class PipelineInput(Input):
    scenario: Literal["normal", "transient", "unavailable", "stale", "new_hire", "duplicate", "growth", "malformed"] = "normal"
    volume: int = Field(default=5000, ge=22, le=5000)


class TicketStatus(Input):
    status: Literal["open", "in_progress", "resolved"]


class TaskStatus(Input):
    status: Literal["pending", "completed"]


class DeliveryInput(Input):
    failures: int = Field(default=0, ge=0, le=1500)


class KnowledgeInput(Input):
    available: bool


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        bootstrap(settings)
        yield

    app = FastAPI(title="PeopleOps AI · Local Simulation", version="0.1.0", lifespan=lifespan,
                  description="Fictional employees and mocked enterprise APIs. Policy answers use cited extractive retrieval; no live LLM.")
    app.state.settings = settings
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])

    @app.middleware("http")
    async def observe(request: Request, call_next):
        started, status = perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
                if request.url.path not in {"/docs", "/redoc"} else
                "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
            )
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            try:
                with connect(settings) as conn:
                    conn.execute("INSERT INTO http_observations(created_at,route,method,status_code,duration_ms) VALUES(?,?,?,?,?)",
                                 (utcnow(), route, request.method, status, round((perf_counter()-started)*1000, 2)))
                    conn.execute("DELETE FROM http_observations WHERE id <= (SELECT COALESCE(MAX(id),0)-1000 FROM http_observations)")
            except sqlite3.Error:
                logging.getLogger("peopleops").error("telemetry_write_failed")

    def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        with connect(settings) as conn:
            digest = hashlib.sha256(credentials.credentials.encode()).hexdigest() if credentials else ""
            principal = conn.execute("SELECT principal_id,label,role,employee_id FROM principals WHERE token_hash=?", (digest,)).fetchone()
            if not principal:
                audit(conn, "anonymous", "authentication", "api", "denied")
        if not principal:
            raise HTTPException(401, "A valid Bearer token is required", headers={"WWW-Authenticate": "Bearer"})
        return dict(principal)

    User = Annotated[dict, Depends(current_user)]

    def allow(user: dict, roles: set[str], action: str, target="api"):
        if user["role"] not in roles:
            with connect(settings) as conn:
                audit(conn, user["principal_id"], action, target, "denied")
            raise HTTPException(403, "This role cannot perform that action")

    def own(user: dict, employee_id: str, action: str):
        if user["role"] == "hr" or (user["role"] == "employee" and user["employee_id"] == employee_id):
            return
        with connect(settings) as conn:
            audit(conn, user["principal_id"], action, employee_id, "denied")
        raise HTTPException(403, "Employee records are limited to their owner and HR")

    @app.get("/health", tags=["operations"])
    def health():
        with connect(settings) as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "simulation": True}

    @app.get("/ready", tags=["operations"])
    def ready():
        with connect(settings) as conn:
            state = freshness(conn)
        healthy = state["state"] == "fresh" and state["latest_run_status"] == "success"
        return JSONResponse({"status": "ready" if healthy else "degraded"}, status_code=200 if healthy else 503)

    @app.get("/api/demo/identities", tags=["demo"])
    def identities():
        if not settings.demo_mode:
            raise HTTPException(404, "Demo identity switching is disabled")
        return json.loads((settings.data_dir / "demo-identities.json").read_text())

    @app.get("/api/me", tags=["identity"])
    def me(user: User):
        return user

    @app.get("/api/metrics", tags=["analytics"])
    def get_metrics(user: User):
        allow(user, {"hr", "analyst"}, "metrics.read")
        with connect(settings) as conn:
            result = metrics(conn, settings)
            audit(conn, user["principal_id"], "metrics.read", "aggregate")
        return result

    @app.get("/api/employees", tags=["employees"])
    def employees(user: User, limit: int = 100, offset: int = 0):
        allow(user, {"hr"}, "employees.list")
        if not 1 <= limit <= 200 or offset < 0:
            raise HTTPException(422, "limit must be 1–200; offset must be nonnegative")
        with connect(settings) as conn:
            result = rows(conn, "SELECT employee_id,full_name,email,department,status,hire_date FROM employees ORDER BY employee_id LIMIT ? OFFSET ?", (limit, offset))
            total = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            audit(conn, user["principal_id"], "employees.list", "directory", count=len(result))
        return {"items": result, "total": total, "limit": limit, "offset": offset}

    @app.get("/api/employees/{employee_id}", tags=["employees"])
    def employee(employee_id: str, user: User):
        own(user, employee_id, "employee.read")
        with connect(settings) as conn:
            row = conn.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone()
            audit(conn, user["principal_id"], "employee.read", employee_id)
        if not row:
            raise HTTPException(404, "Employee not found")
        return dict(row)

    @app.get("/api/requests", tags=["requests"])
    def requests(user: User, status: Literal["open", "in_progress", "resolved"] | None = None):
        allow(user, {"employee", "hr"}, "requests.list")
        with connect(settings) as conn:
            result = rows(conn, """SELECT r.*,e.full_name FROM hr_requests r JOIN employees e USING(employee_id)
                WHERE (?='hr' OR r.employee_id=?) AND (? IS NULL OR r.status=?) ORDER BY r.created_at DESC LIMIT 200""",
                (user["role"], user["employee_id"], status, status))
            audit(conn, user["principal_id"], "requests.list", "queue", count=len(result))
        return result

    @app.post("/api/requests", tags=["requests"])
    def submit_request(payload: TicketInput, response: Response, user: User,
                       idempotency_key: Annotated[str, Header(min_length=8, max_length=128)]):
        allow(user, {"employee", "hr"}, "request.create")
        employee_id = payload.employee_id or user["employee_id"]
        if not employee_id:
            raise HTTPException(422, "HR must select an employee")
        own(user, employee_id, "request.create")
        content = {**payload.model_dump(), "employee_id": employee_id}
        digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
        with connect(settings) as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT * FROM hr_requests WHERE employee_id=? AND idempotency_key=?", (employee_id, idempotency_key)).fetchone()
            if previous:
                if previous["payload_hash"] != digest:
                    raise HTTPException(409, "This idempotency key was already used for different content")
                audit(conn, user["principal_id"], "request.replay", previous["request_id"])
                return {"request": dict(previous), "replayed": True}
            if not conn.execute("SELECT 1 FROM employees WHERE employee_id=?", (employee_id,)).fetchone():
                raise HTTPException(404, "Employee not found")
            route = route_request(payload.subject + " " + payload.description)
            request_id, now = "HR-" + uuid4().hex[:10].upper(), utcnow()
            conn.execute("INSERT INTO hr_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (request_id, employee_id, payload.subject, payload.description, route["category"], route["team"], route["confidence"],
                          "open", payload.priority, now, now, None, idempotency_key, digest))
            result = dict(conn.execute("SELECT * FROM hr_requests WHERE request_id=?", (request_id,)).fetchone())
            audit(conn, user["principal_id"], "request.create", request_id, category=route["category"])
        response.status_code = 201
        return {"request": result, "replayed": False}

    @app.patch("/api/requests/{request_id}", tags=["requests"])
    def update_request(request_id: str, payload: TicketStatus, user: User):
        allow(user, {"hr"}, "request.update", request_id)
        with connect(settings) as conn:
            cursor = conn.execute("UPDATE hr_requests SET status=?,updated_at=?,resolved_at=? WHERE request_id=?",
                                  (payload.status, utcnow(), utcnow() if payload.status == "resolved" else None, request_id))
            if cursor.rowcount == 0:
                raise HTTPException(404, "Request not found")
            audit(conn, user["principal_id"], "request.update", request_id, status=payload.status)
        return {"request_id": request_id, "status": payload.status}

    @app.get("/api/onboarding", tags=["onboarding"])
    def tasks(user: User):
        allow(user, {"employee", "hr"}, "onboarding.list")
        with connect(settings) as conn:
            result = rows(conn, """SELECT t.*,e.full_name FROM onboarding_tasks t JOIN employees e USING(employee_id)
                WHERE (?='hr' OR t.employee_id=?) ORDER BY t.due_date,t.employee_id,t.kind LIMIT 300""", (user["role"], user["employee_id"]))
            audit(conn, user["principal_id"], "onboarding.list", "tasks", count=len(result))
        return result

    @app.patch("/api/onboarding/{task_id}", tags=["onboarding"])
    def update_task(task_id: str, payload: TaskStatus, user: User):
        with connect(settings) as conn:
            task = conn.execute("SELECT * FROM onboarding_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(404, "Task not found")
        own(user, task["employee_id"], "onboarding.update")
        with connect(settings) as conn:
            conn.execute("UPDATE onboarding_tasks SET status=?,completed_at=? WHERE task_id=?", (payload.status, utcnow() if payload.status == "completed" else None, task_id))
            audit(conn, user["principal_id"], "onboarding.update", task_id, status=payload.status)
        return {"task_id": task_id, "status": payload.status}

    @app.get("/api/policies", tags=["policies"])
    def policies(user: User):
        with connect(settings) as conn:
            result = visible_policies(conn, user["role"])
            audit(conn, user["principal_id"], "policies.list", "knowledge", count=len(result))
        return result

    @app.get("/api/policies/{policy_id}", tags=["policies"])
    def policy(policy_id: str, user: User):
        with connect(settings) as conn:
            result = [row for row in visible_policies(conn, user["role"]) if row["policy_id"] == policy_id]
            audit(conn, user["principal_id"], "policy.read", policy_id, "allowed" if result else "denied")
        if not result:
            raise HTTPException(404, "Policy unavailable")
        return result[0]

    @app.post("/api/assistant", tags=["assistant"])
    def assistant(payload: QuestionInput, user: User):
        with connect(settings) as conn:
            result = answer_question(conn, payload.question, user["role"])
            audit(conn, user["principal_id"], "assistant.answer", "knowledge", escalated=result["escalated"], citations=len(result["citations"]))
        return result

    @app.get("/api/ops", tags=["operations"])
    def ops(user: User):
        allow(user, {"hr"}, "operations.read")
        with connect(settings) as conn:
            result = operations(conn)
        return result

    @app.post("/api/ops/pipeline", tags=["operations"])
    def pipeline(payload: PipelineInput, user: User):
        allow(user, {"hr"}, "pipeline.run")
        result = ingest(settings, payload.scenario, payload.volume, user["principal_id"])
        return JSONResponse(result, status_code=200 if result["status"] == "success" else 503)

    @app.post("/api/ops/reminders", tags=["operations"])
    def reminders(user: User):
        allow(user, {"hr"}, "reminders.queue")
        return queue_reminders(settings, user["principal_id"])

    @app.post("/api/ops/deliver", tags=["operations"])
    def drain(payload: DeliveryInput, user: User):
        allow(user, {"hr"}, "notifications.drain")
        return deliver(settings, payload.failures, user["principal_id"])

    @app.post("/api/ops/knowledge", tags=["operations"])
    def knowledge(payload: KnowledgeInput, user: User):
        allow(user, {"hr"}, "knowledge.simulate")
        with connect(settings) as conn:
            conn.execute("UPDATE policies SET available=?", (int(payload.available),))
            audit(conn, user["principal_id"], "knowledge.simulate", "policies", available=payload.available)
        return {"available": payload.available}

    @app.get("/api/notifications", tags=["operations"])
    def notifications(user: User):
        allow(user, {"hr"}, "notifications.read")
        with connect(settings) as conn:
            return rows(conn, "SELECT * FROM slack_messages ORDER BY created_at DESC LIMIT 100")

    @app.get("/api/audit", tags=["operations"])
    def logs(user: User):
        allow(user, {"hr"}, "audit.read")
        with connect(settings) as conn:
            result = rows(conn, "SELECT * FROM audit_logs ORDER BY audit_id DESC LIMIT 100")
            audit(conn, user["principal_id"], "audit.read", "audit_logs")
        return result

    @app.get("/api/demo/source", tags=["demo"])
    def preview_source(user: User):
        allow(user, {"hr"}, "source.preview")
        fields = {"employee_id", "full_name", "email", "status", "hire_date"}
        return [{k: v for k, v in row.items() if k in fields} for row in source_records(settings)]

    app.mount("/static", StaticFiles(directory=PACKAGE / "web"), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(PACKAGE / "web" / "index.html")

    return app


app = create_app()
