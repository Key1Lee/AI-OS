"""Offline enterprise HR reference entrypoint: uvicorn app.main:app --port 8811."""
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from threading import Lock
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.audit import configure_logging, metrics, write_audit
from app.auth import authenticate_session, verify_slack
from app.identity import SQLiteIdentityProvider
from app.diagnostics import ExecutionTrace
from app.enterprise_data import seed_enterprise_data
from app.middleware import RequestSizeLimit
from app.mock_store import transaction
from app.models import AskRequest, ExecutionStage, HRResponse, SlackEnvelope, SimulationRequest, SourceAccess, TestRunRequest
from app.orchestrator import Orchestrator
from app.settings import HRSettings
from app.rules import RuleBook
from app.test_runner import JobError, TestJobRunner
from app.workday_client import MockWorkdayClient, MockWorkdayTransport
from ingestion.run_pipeline import run_pipeline


class RateLimiter:
    def __init__(self, limit):
        self.limit, self.windows, self.lock = limit, defaultdict(deque), Lock()

    def check(self, principal, now=None):
        """Bound each authenticated identity's local request rate before source access."""
        clock = time.monotonic() if now is None else now
        key = (principal.tenant, principal.employee_id)
        with self.lock:
            events = self.windows[key]
            while events and events[0] <= clock - 60:
                events.popleft()
            if len(events) >= self.limit:
                raise HTTPException(429, "Request limit reached", headers={"Retry-After": "60"})
            events.append(clock)


def create_app(settings=None, workday=None, retriever=None, router=None, test_runner=None):
    """Wire injected domain functions into a bounded, authenticated mock HTTP application."""
    settings = settings or HRSettings.configured()
    configure_logging()
    rules = RuleBook(settings.rules_root)
    identities = SQLiteIdentityProvider(settings)
    workday = workday or MockWorkdayClient(settings, rulebook=rules)
    orchestrator = Orchestrator(settings, workday, router=router, rulebook=rules, **({"retriever": retriever} if retriever else {}))
    jobs = test_runner or TestJobRunner(settings.lab_reports_path, settings.lab_job_timeout_seconds)
    limiter = RateLimiter(settings.max_requests_per_minute)

    @asynccontextmanager
    async def lifespan(application):
        seed_enterprise_data(settings)
        run_pipeline(settings)
        try:
            yield
        finally:
            jobs.close()

    application = FastAPI(title="Fictional enterprise HR assistant", version="2.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    application.add_middleware(RequestSizeLimit, max_bytes=32_000)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "api", "host.docker.internal"])
    application.state.settings = settings
    application.state.workday = workday
    application.state.orchestrator = orchestrator
    application.state.test_runner = jobs
    application.state.rules = rules

    def principal(request: Request, authorization: str | None = Header(default=None)):
        with request.state.execution.step("authentication", ["SEC-SESSION"]):
            return authenticate_session(authorization, identities)

    def administrator(actor=Depends(principal)):
        if "audit:read" not in actor.permissions:
            raise HTTPException(403, "Access denied")
        return actor

    @application.middleware("http")
    async def correlation(request, call_next):
        request.state.request_id = str(uuid4())
        request.state.started = time.perf_counter()
        request.state.execution = ExecutionTrace()
        response = await call_next(request)
        response.headers.update({"X-Request-ID": getattr(request.state, "response_request_id", request.state.request_id),
                                 "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'"})
        return response

    @application.exception_handler(HTTPException)
    async def denied_request(request, error):
        with transaction(settings.database_path) as conn:
            write_audit(conn, {"event": "request_rejected", "request_id": request.state.request_id,
                               "status": "denied" if error.status_code in (401, 403) else "invalid", "decision": "denied"})
        return JSONResponse(status_code=error.status_code, content=error_payload(request, error.detail, "request_rejected"), headers=error.headers)

    def error_payload(request, detail, code):
        stages = request.state.execution.complete()
        for stage in stages:
            if stage.status == "failed":
                stage.failure_code = "invalid_slack_signature" if stage.stage == "slack_signature" else code
        return {"detail": detail, "request_id": request.state.request_id, "failure_code": code,
                "handled_safely": True, "execution_trace": [s.model_dump() for s in stages],
                "duration_ms": round((time.perf_counter()-request.state.started)*1000, 4), "sources": [],
                "applied_rules": [rules.match(rule_id, stage.status).model_dump() for stage in stages for rule_id in stage.rule_ids if rule_id in rules.catalog]}

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse(status_code=422, content=error_payload(request, "Invalid request", "invalid_request"))

    @application.exception_handler(sqlite3.Error)
    async def storage_failure(request, error):
        return JSONResponse(status_code=503, content=error_payload(request, "HR storage unavailable", "storage_unavailable"))

    @application.exception_handler(JobError)
    async def job_failure(request, error):
        return JSONResponse(status_code=error.status_code, content=error_payload(request, error.code, error.code))

    def execute(request, actor, question, event_id=None, raw_body=b"", selected_orchestrator=None):
        limiter.check(actor)
        with transaction(settings.database_path, immediate=True) as conn:
            if event_id:
                receipt_start = time.perf_counter()
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event_id):
                    raise HTTPException(422, "Invalid event identifier")
                # A receipt cannot restore access after grants, inventory or applicability change.
                authority = actor.model_dump_json()+settings.as_of_date.isoformat()+rules.business.model_dump_json()+rules.security.model_dump_json()
                inventory = [tuple(row) for row in conn.execute("SELECT r.document_id,r.version,r.metadata,r.digest FROM registry r JOIN inventory_membership i USING(document_id,version) ORDER BY r.document_id,r.version")]
                body_hash = hashlib.sha256(raw_body+authority.encode()+json.dumps(inventory).encode()).hexdigest()
                key = (actor.tenant, actor.employee_id, event_id)
                conn.execute("DELETE FROM receipts WHERE expires_at<?", (time.time(),))
                receipt = conn.execute("SELECT * FROM receipts WHERE tenant=? AND actor=? AND event_id=?", key).fetchone()
                if receipt:
                    if receipt["body_hash"] != body_hash:
                        raise HTTPException(409, "Event identifier conflicts with an earlier request")
                    decode_start = time.perf_counter()
                    cached = HRResponse.model_validate_json(receipt["response"])
                    cached.replayed = True
                    cached.trace = ["enterprise_identity", "idempotency_receipt", "response"]
                    replay_trace = ExecutionTrace()
                    replay_trace.stages = [*request.state.execution.stages,
                        ExecutionStage(stage="idempotency", status="replayed", duration_ms=round((decode_start-receipt_start)*1000, 4), rule_ids=["SEC-RECEIPT"]),
                        ExecutionStage(stage="response", status="passed", duration_ms=round((time.perf_counter()-decode_start)*1000, 4))]
                    cached.execution_trace = replay_trace.complete()
                    cached.sources = [SourceAccess(system="identity_service", access="accessed", operation="authenticate_session", duration_ms=sum(s.duration_ms for s in request.state.execution.stages if s.stage == "authentication"), returned_count=1, attempts=1)]
                    cached.applied_rules = [rules.match("SEC-SESSION", "authenticated"), rules.match("SEC-RECEIPT", "authority_snapshot_validated"), *[r.model_copy(update={"outcome":"prior_receipt"}) for r in cached.applied_rules if r.rule_id not in ("SEC-SESSION", "SEC-RECEIPT")]]
                    cached.duration_ms = round((time.perf_counter()-request.state.started)*1000, 4)
                    request.state.response_request_id = cached.request_id
                    write_audit(conn, {"event": "duplicate_replayed", "request_id": cached.request_id, "status": cached.status, "decision": "cached"})
                    return cached
            response = (selected_orchestrator or orchestrator).handle(conn, actor, question, request.state.request_id)
            initial = request.state.execution.stages
            already = {s.stage for s in initial}
            response.execution_trace = [*initial, *[s for s in response.execution_trace if s.stage not in already]]
            response.sources.insert(0, SourceAccess(system="identity_service", access="accessed", operation="authenticate_session", duration_ms=sum(s.duration_ms for s in initial if s.stage == "authentication"), returned_count=1, attempts=1, fields=["role", "country", "permissions"]))
            response.applied_rules.insert(0, rules.match("SEC-SESSION", "authenticated"))
            response.duration_ms = round((time.perf_counter()-request.state.started)*1000, 4)
            if request.url.path == "/slack/events":
                response.trace = ["slack_signature", "enterprise_identity", "slack_identity_binding", *response.trace[1:]]
                response.applied_rules.insert(0, rules.match("SEC-SLACK", "verified_and_bound"))
            if event_id:
                conn.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (*key, body_hash, response.model_dump_json(), time.time() + settings.receipt_ttl_seconds))
            return response

    @application.post("/ask", response_model=HRResponse)
    @application.post("/chat", response_model=HRResponse)
    def ask(body: AskRequest, request: Request, actor=Depends(principal), idempotency_key: str | None = Header(default=None)):
        return execute(request, actor, body.question, idempotency_key, body.model_dump_json().encode())

    @application.post("/slack/events", response_model=HRResponse)
    async def slack(request: Request):
        raw = await request.body()
        with request.state.execution.step("slack_signature", ["SEC-SLACK"]):
            verify_slack(raw, request.headers.get("x-slack-request-timestamp"), request.headers.get("x-slack-signature"), settings)
        actor = principal(request, request.headers.get("authorization"))
        try:
            event = SlackEnvelope.model_validate_json(raw)
        except ValidationError as error:
            raise HTTPException(422, "Invalid Slack envelope") from error
        with request.state.execution.step("slack_identity_binding", ["SEC-SLACK"]):
            if not identities.bind_slack(actor, event.team_id, event.event.user):
                raise HTTPException(403, "Identity binding failed")
        return execute(request, actor, event.event.text, event.event_id, raw)

    def lab_only():
        if not settings.demo_mode or not settings.lab_enabled:
            raise HTTPException(404, "Not found")

    def lab_operator(request: Request, actor=Depends(principal)):
        with request.state.execution.step("authorization", ["SEC-LAB-RUN"]):
            lab_only()
            if rules.security.test_runner_permission not in actor.permissions:
                raise HTTPException(403, "Access denied")
        return actor

    @application.get("/lab/info")
    def lab_info(actor=Depends(principal)):
        lab_only()
        return {"fictional_demo_only": True, "can_run_tests": rules.security.test_runner_permission in actor.permissions,
                "suites": ["unit", "integration", "security", "evaluations"], "job_timeout_seconds": settings.lab_job_timeout_seconds,
                "business_date": settings.as_of_date, "database": "SQLite synthetic identity and Workday records",
                "max_concurrent_jobs": 1}

    @application.post("/lab/ask", response_model=HRResponse)
    def simulate(body: SimulationRequest, request: Request, actor=Depends(principal)):
        lab_only()
        transport = MockWorkdayTransport(scenario=body.scenario, database_path=settings.database_path)
        source = MockWorkdayClient(settings, transport, rulebook=rules)
        simulation = Orchestrator(settings, source, retriever=orchestrator.retriever, router=orchestrator.router, rulebook=rules)
        return execute(request, actor, body.question, selected_orchestrator=simulation)

    @application.post("/admin/test-runs", status_code=202)
    def start_tests(body: TestRunRequest, actor=Depends(lab_operator)):
        return jobs.start(body.suite, actor.tenant)

    @application.get("/admin/test-runs")
    def recent_tests(actor=Depends(lab_operator)):
        return {"jobs": jobs.recent(actor.tenant)}

    @application.get("/admin/test-runs/{job_id}")
    def test_result(job_id: str, actor=Depends(lab_operator)):
        return jobs.get(job_id, actor.tenant)

    @application.post("/admin/ingest")
    def ingest(actor=Depends(principal)):
        if "policy:ingest" not in actor.permissions:
            raise HTTPException(403, "Access denied")
        try:
            return run_pipeline(settings)
        except ValueError as error:
            raise HTTPException(409, "Governed source validation failed; index update was rolled back") from error

    @application.get("/admin/observability")
    def observations(actor=Depends(administrator)):
        with transaction(settings.database_path) as conn:
            return metrics(conn)

    @application.get("/admin/audit/{request_id}")
    def audit_events(request_id: str, actor=Depends(administrator)):
        with transaction(settings.database_path) as conn:
            return {"events": [json.loads(row[0]) for row in conn.execute("SELECT event FROM audits WHERE request_id=? ORDER BY sequence", (request_id,))]}

    @application.get("/health")
    def health(actor=Depends(administrator)):
        with transaction(settings.database_path) as conn:
            conn.execute("SELECT 1 FROM registry LIMIT 1")
        return {"status": "ok", "mode": "enterprise_mock", "business_date": settings.as_of_date}

    @application.get("/live")
    def live():
        return {"status": "ok"}

    @application.get("/demo/identities")
    def demo_identities():
        if not settings.demo_mode:
            raise HTTPException(404, "Not found")
        return {"fictional_demo_only": True, "identities": identities.demo_identities()}

    @application.get("/me")
    def me(actor=Depends(principal)):
        return {"identity": {"subject": "Fictional employee", "region": actor.country, "role": actor.role}, "mode": "Enterprise mock · deterministic sources"}

    static = Path(__file__).with_name("enterprise_static")
    static.mkdir(exist_ok=True)
    application.mount("/assets", StaticFiles(directory=static), name="enterprise_assets")

    @application.get("/", include_in_schema=False)
    def home():
        return FileResponse(static / "index.html")

    return application


app = create_app()
