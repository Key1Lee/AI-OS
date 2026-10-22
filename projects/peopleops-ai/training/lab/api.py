from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import secrets
from time import perf_counter
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from lab.config import Settings
from lab.contracts import ActionResult, Answer, Confirmation, Health, PendingExercise, Principal, Question, RequestStatus
from lab.db import make_engine, session_factory
from lab.fixtures import load
from lab.providers import make_provider
from lab.telemetry import ObservedProvider, Telemetry
from exercises.e08_endpoints import build_router
from exercises import e06_grounding, e09_planning, e10_actions, e13_status


def create_app(engine=None, settings=None):
    settings = settings or Settings()
    engine = engine if engine is not None else make_engine(settings.database_url)
    sessions = session_factory(engine)
    telemetry = Telemetry()
    provider = ObservedProvider(make_provider(settings), telemetry)
    identities = [{"name": name, "employee_id": employee, "role": role, "token": secrets.token_urlsafe(32)} for name, employee, role in [
        ("Maya · Employee", "EMP-001", "employee"), ("Team manager", "EMP-002", "manager"),
        ("Recruiter", "EMP-003", "recruiter"), ("HR administrator", "EMP-004", "hr_admin"),
        ("People analyst", "EMP-005", "analyst")]]
    principals = {i["token"]: Principal(employee_id=i["employee_id"], role=i["role"]) for i in identities}

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="PeopleOps AI · Interview Lab", version="0.2.0", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "api", "testserver"])
    app.state.telemetry = telemetry
    bearer = HTTPBearer(auto_error=False)

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        value = principals.get(credentials.credentials) if credentials else None
        if value is None:
            raise HTTPException(401, "Choose a local demo identity", headers={"WWW-Authenticate": "Bearer"})
        return value

    def session():
        with sessions.begin() as value:
            yield value

    @app.middleware("http")
    async def observe(request: Request, call_next):
        start, status = perf_counter(), 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        finally:
            route = request.scope.get("route")
            telemetry.record(kind="http", route=getattr(route, "path", "unmatched"), status=status,
                             latency_ms=round((perf_counter() - start) * 1000, 2))

    @app.exception_handler(PendingExercise)
    async def pending(request, exc):
        return JSONResponse(status_code=501, content={"status": "exercise_pending", "exercise": exc.exercise,
                                                      "message": "This business capability is a learner exercise. No action was executed."})

    @app.exception_handler(SQLAlchemyError)
    async def unavailable(request, exc):
        return JSONResponse(status_code=503, content={"status": "unavailable", "message": "Database unavailable; retry after recovery."})

    @app.get("/health", response_model=Health)
    def health():
        return Health(status="ok")

    @app.get("/ready", response_model=Health)
    def ready(db=Depends(session)):
        db.execute(text("SELECT 1 FROM seed_markers WHERE version='training-v1'")).one()
        return Health(status="ready")

    @app.get("/lab/identities")
    def demo_identities():
        return identities  # Deliberately public local identity simulator; NOT production login.

    @app.get("/lab/catalog")
    def catalog():
        data = load()
        return {"metadata": data["metadata"], "counts": {name: len(data[name]) for name in
                ["employees", "jobs", "candidates", "recruiting_events", "policies", "tickets", "onboarding_tasks"]},
                "exercises": json.loads((Path(__file__).parent.parent / "fixtures" / "curriculum.json").read_text())}

    @app.get("/lab/fixtures/{name}")
    def fixture(name: str):
        data = load()
        if name not in data or not isinstance(data[name], list):
            raise HTTPException(404, "Unknown fixture")
        return {"synthetic": True, "purpose": "developer fixture explorer; bypasses business authorization", "rows": data[name]}

    @app.get("/lab/telemetry")
    def observations():
        return telemetry.summary()

    @app.post("/lab/provider-probe")
    def provider_probe():
        # Fixed benign payload only, never an arbitrary prompt/data exfiltration proxy.
        result = provider.complete("Say hello to a synthetic training environment.")
        return {"provider": settings.llm_provider, "text": result.text, "usage_kind": result.usage_kind,
                "input": result.input_tokens, "output": result.output_tokens}

    @app.get("/api/me", response_model=Principal)
    def me(actor=Depends(principal)):
        return actor

    @app.post("/api/assistant", response_model=Answer)
    def answer(question: Question, actor=Depends(principal), db=Depends(session)):
        return e06_grounding.answer_question(question.text, actor, db, provider)

    @app.post("/api/actions/prepare")
    def prepare(question: Question, actor=Depends(principal), db=Depends(session)):
        plan = e09_planning.plan_action(question.text, actor)
        if plan.tool == "clarify":
            return {"status": "clarify", "summary": plan.summary}
        return e10_actions.prepare_action(plan, actor, db, datetime.now(timezone.utc))

    @app.post("/api/actions/confirm", response_model=ActionResult)
    def confirm(body: Confirmation, actor=Depends(principal), db=Depends(session)):
        telemetry.record(kind="tool", name="execute_action", actor_id=actor.employee_id)
        return e10_actions.execute_action(body, actor, db, datetime.now(timezone.utc))

    @app.get("/api/requests/{request_id}", response_model=RequestStatus)
    def status(request_id: str, actor=Depends(principal), db=Depends(session)):
        return e13_status.request_status(request_id, actor, db)

    app.include_router(build_router(principal, session))
    return app


app = create_app()
