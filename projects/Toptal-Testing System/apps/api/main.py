from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError
from data_system_map.api.boundary import install_local_boundary

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
    install_local_boundary(application,token,token_header='X-Trainer-Token')

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
