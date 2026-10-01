from __future__ import annotations

import logging
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from sqlalchemy.exc import OperationalError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from trainer.config import ROOT, Settings
from trainer.execution.sql import ExecutionUnavailable, SqlRunner
from trainer.exercises.bank import Bank
from trainer.repositories.store import Store
from trainer.schemas.models import ClarificationRequest, DraftRequest, RunRequest, StartRequest, SubmitRequest
from trainer.services.training import Conflict, TrainingService


def create_app(settings: Settings | None = None, *, runner=None, clock=None) -> FastAPI:
    settings = settings or Settings.from_env()
    bank = Bank(settings.root)
    store = Store(settings.database_path)
    store.migrate()
    store.seed(bank)
    executor = runner or SqlRunner(settings)
    service = TrainingService(store,bank,executor,**({"clock":clock} if clock else {}))
    token = secrets.token_urlsafe(32)
    application = FastAPI(title="Senior AE Trainer",version="0.1.0",docs_url=None,redoc_url=None,openapi_url="/api/openapi.json")
    application.state.service, application.state.store = service, store
    application.add_middleware(TrustedHostMiddleware,allowed_hosts=["127.0.0.1","localhost","testserver"])

    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST","PUT","PATCH","DELETE"}:
            origin = request.headers.get("origin")
            if origin and (urlsplit(origin).netloc != request.url.netloc or urlsplit(origin).scheme != request.url.scheme):
                return JSONResponse(status_code=403,content={"detail":"Mutation requests must come from this local application."})
            if not secrets.compare_digest(request.headers.get("x-trainer-token", ""),token):
                return JSONResponse(status_code=403,content={"detail":"Refresh the application to obtain the current local request token."})
        if request.url.path.startswith('/api/map') and request.method in {'POST','PUT','PATCH'}:
            limit = 8 * 1024 * 1024
            too_large = JSONResponse(status_code=413,content={'detail':'Map artifact uploads are limited to 8 MiB.'})
            length = request.headers.get('content-length')
            if length and length.isdigit() and int(length) > limit:
                return too_large
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > limit:
                    return too_large
                body.extend(chunk)
            # Starlette's Request.body() cache is replayed by BaseHTTPMiddleware
            # to downstream JSON parsing. Populate it only after bounded reading.
            request._body = bytes(body)
        response = await call_next(request)
        response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer","Cache-Control":"no-store",
            "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"})
        return response

    @application.exception_handler(RequestValidationError)
    async def validation(request, exc):
        if request.url.path.startswith('/api/map'):
            return JSONResponse(status_code=422,content={'detail':'The request does not match the Data System Map contract. Check required fields and types.'})
        return await request_validation_exception_handler(request,exc)

    @application.exception_handler(Conflict)
    async def conflict(_, exc):
        return JSONResponse(status_code=409,content={"detail":str(exc)})

    @application.exception_handler(KeyError)
    async def missing(_, exc):
        return JSONResponse(status_code=404,content={"detail":"Resource not found."})

    @application.exception_handler(ExecutionUnavailable)
    async def unavailable(_, exc):
        return JSONResponse(status_code=503,content={"detail":str(exc)})

    @application.exception_handler(OperationalError)
    async def storage_failure(_, exc):
        logging.getLogger(__name__).error('{"event":"storage_unavailable"}')
        return JSONResponse(status_code=503,content={"detail":"Training storage is unavailable. Keep your local draft and retry."})

    @application.get("/api/health")
    def health():
        return {"status":"ok","service":"senior-ae-trainer","sql_available":executor.supported,"exercises":len(bank.exercises)}

    @application.get("/api/config")
    def config():
        return {"request_token":token,"sql_available":executor.supported,"reasoning_available":False,"policy_version":"ae-v1"}

    @application.get("/api/dashboard")
    def dashboard():
        return service.dashboard()

    @application.get("/api/exercises")
    def exercises():
        return [e.public() for e in bank.exercises.values()]

    @application.get("/api/exercises/{key}")
    def exercise(key: str):
        return bank.exercises[key].public()

    @application.post("/api/attempts",status_code=201)
    def start(payload: StartRequest):
        return service.start(payload)

    @application.get("/api/attempts/{key}")
    def attempt(key: str):
        return service.attempt(key)

    @application.put("/api/attempts/{key}/draft")
    def draft(key: str, payload: DraftRequest):
        return service.save(key,payload)

    @application.post("/api/attempts/{key}/run")
    def run(key: str, payload: RunRequest):
        return service.run(key,payload.code)

    @application.post("/api/attempts/{key}/submit")
    def submit(key: str, payload: SubmitRequest):
        return service.submit(key,payload)

    @application.post("/api/attempts/{key}/revise",status_code=201)
    def revise(key: str):
        return service.revise(key)

    @application.post("/api/attempts/{key}/hints")
    def hint(key: str):
        return service.hint(key)

    @application.post("/api/attempts/{key}/solution")
    def solution(key: str):
        return service.solution(key)

    @application.post("/api/attempts/{key}/clarifications")
    def clarify(key: str,payload: ClarificationRequest):
        return service.clarify(key,payload.question)

    @application.post("/api/attempts/{key}/pause")
    def pause(key: str):
        return service.pause(key)

    @application.post("/api/attempts/{key}/resume")
    def resume(key: str):
        return service.resume(key)

    @application.get("/api/competencies")
    def competencies():
        return service.dashboard()["competencies"]

    @application.get("/api/competencies/{key}")
    def competency(key: str):
        rows = service.dashboard()["competencies"]
        match = next((c for c in rows if c["id"] == key),None)
        if not match: raise KeyError(key)
        return match

    @application.get("/api/mistakes")
    def mistakes():
        return service.dashboard()["mistakes"]

    @application.get("/api/reviews")
    def reviews():
        return service.dashboard()["reviews"]

    @application.get("/api/history")
    def history():
        return service.dashboard()["history"]

    from apps.api.data_map import mount_data_map
    mount_data_map(application,settings)

    static = ROOT / "apps/web/dist"
    if (static / "assets").exists():
        application.mount("/assets",StaticFiles(directory=static / "assets"),name="assets")

    @application.get("/",include_in_schema=False)
    @application.get("/map",include_in_schema=False)
    def index():
        if not (static / "index.html").exists():
            raise HTTPException(status_code=503,detail="Build the local UI using make setup, then restart the trainer.")
        return FileResponse(static / "index.html")

    return application
