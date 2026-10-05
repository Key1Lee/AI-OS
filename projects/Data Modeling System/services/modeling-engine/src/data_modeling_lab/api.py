from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .contracts import (
    BuildRequest, BuildResult, EvaluationResult, GrainRequest, GrainResult, JoinRequest,
    JoinResult, MetricDefinition, MetricRequest, ModelDefinition, ScenarioDefinition,
    StagingRequest, StagingResult,
)
from .engine import ModelingEngine
from .sql import LabError


def create_app(engine: ModelingEngine | None = None, web_dir: Path | None = None) -> FastAPI:
    engine = engine or ModelingEngine()
    app = FastAPI(title="Data Modeling & Transformation Lab", version="0.1.0", description="Independent deterministic modeling exercises; no assessment scoring or runtime monitoring.")

    @app.exception_handler(LabError)
    async def lab_error(_request: Request, exc: LabError):
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}})

    @app.get("/api/health")
    def health():
        return {"status": "ready", "contract_version": "modeling-lab-v1", "execution": "local DuckDB"}

    @app.get("/api/scenario", response_model=ScenarioDefinition)
    def scenario():
        return engine.scenario()

    @app.post("/api/grain", response_model=GrainResult)
    def declare_grain(request: GrainRequest):
        return engine.declare_grain(request)

    @app.post("/api/staging", response_model=StagingResult)
    def stage(request: StagingRequest):
        return engine.stage(request)

    @app.post("/api/join", response_model=JoinResult)
    def join(request: JoinRequest):
        return engine.join(request)

    @app.post("/api/build", response_model=BuildResult)
    def build(request: BuildRequest):
        return engine.build(request)

    @app.post("/api/metric", response_model=MetricDefinition)
    def metric(request: MetricRequest):
        return engine.metric(request)

    @app.get("/api/contracts")
    def contracts():
        return {"contract_version": "modeling-lab-v1", "purpose": "Designed modeling state; consumer-owned adapters can compare it with observed state.",
                "scenario": engine.scenario().model_dump(mode="json"),
                "schemas": {model.__name__: model.model_json_schema() for model in [ScenarioDefinition, ModelDefinition, EvaluationResult, BuildResult, JoinResult, MetricDefinition]}}

    if web_dir is not None:
        if not (web_dir / "index.html").is_file():
            raise RuntimeError("Build apps/web before starting the production web server.")
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app()
