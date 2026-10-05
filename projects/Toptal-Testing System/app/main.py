from __future__ import annotations

from pathlib import Path
import secrets
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.database import Database
from app.engine import AssessmentEngine, ConfigurationError, InvalidTransition
from app.models import ConfigurationView, ContinueRequest, StartSessionRequest, SubmitRequest
from app.openai_service import InterviewerProvider, InterviewerUnavailable, OpenAIInterviewer


def create_app(
    settings: Settings | None = None,
    *,
    provider: InterviewerProvider | None = None,
    database: Database | None = None,
    require_api_key: bool | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    resolved_database = database or Database(resolved_settings.database_path)
    resolved_database.initialize()
    resolved_provider = provider or OpenAIInterviewer(resolved_settings)
    engine = AssessmentEngine(
        resolved_settings,
        resolved_database,
        resolved_provider,
        require_api_key=(provider is None if require_api_key is None else require_api_key),
    )
    static_dir = Path(__file__).parent / "static"

    application = FastAPI(
        title="Senior FDE Assessment",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
    )
    application.state.settings = resolved_settings
    application.state.database = resolved_database
    application.state.engine = engine
    request_token = secrets.token_urlsafe(32)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    application.mount("/static", StaticFiles(directory=static_dir), name="static")

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        rejection = None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin is not None:
                try:
                    parsed = urlsplit(origin)
                    same_origin = (
                        parsed.scheme in {"http", "https"}
                        and origin == f"{parsed.scheme}://{parsed.netloc}"
                        and parsed.scheme == request.url.scheme
                        and parsed.netloc == request.url.netloc
                        and not (parsed.path or parsed.query or parsed.fragment or parsed.username)
                    )
                except ValueError:
                    same_origin = False
                if not same_origin:
                    rejection = JSONResponse(status_code=403, content={
                        "detail": "Mutation requests must come from this local application.",
                        "code": "local_origin",
                    })
            supplied = request.headers.get("X-Interview-Token", "").encode("utf-8")
            if rejection is None and not secrets.compare_digest(supplied, request_token.encode("ascii")):
                rejection = JSONResponse(status_code=403, content={
                    "detail": "Refresh the application to obtain the current local request token.",
                    "code": "local_token",
                })
        response = rejection if rejection is not None else await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    @application.exception_handler(KeyError)
    async def missing_resource(_: Request, exc: KeyError):
        return JSONResponse(status_code=404, content={"detail": "Assessment session not found"})

    @application.exception_handler(InvalidTransition)
    async def invalid_transition(_: Request, exc: InvalidTransition):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @application.exception_handler(ConfigurationError)
    async def configuration_error(_: Request, exc: ConfigurationError):
        return JSONResponse(status_code=503, content={"detail": str(exc), "code": "configuration_error"})

    @application.exception_handler(InterviewerUnavailable)
    async def interviewer_unavailable(_: Request, exc: InterviewerUnavailable):
        return JSONResponse(status_code=502, content={"detail": str(exc), "code": "interviewer_unavailable"})

    @application.get("/", include_in_schema=False)
    async def index():
        return FileResponse(static_dir / "index.html")

    @application.get("/api/health")
    async def health():
        return {
            "service": "toptal-testing",
            "status": "ok",
            "api_configured": resolved_settings.api_configured,
        }

    @application.get("/api/config", response_model=ConfigurationView)
    async def configuration():
        return ConfigurationView(
            api_configured=resolved_settings.api_configured,
            model=resolved_settings.interviewer_model,
            default_reasoning_effort=resolved_settings.default_reasoning_effort,
            high_reasoning_effort=resolved_settings.high_reasoning_effort,
            request_token=request_token,
        )

    @application.get("/api/sessions")
    async def sessions():
        return [engine.to_view(item) for item in resolved_database.list_sessions()]

    @application.post("/api/sessions", status_code=201)
    async def start_session(payload: StartSessionRequest):
        return engine.start_session(payload.target_role)

    @application.get("/api/sessions/{session_id}")
    async def get_session(session_id: str):
        return engine.to_view(resolved_database.get_session(session_id))

    @application.post("/api/sessions/{session_id}/submit")
    async def submit(session_id: str, payload: SubmitRequest):
        try:
            return engine.submit(session_id, payload)
        except InvalidTransition:
            raise
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.post("/api/sessions/{session_id}/pause")
    async def pause(session_id: str):
        return engine.pause(session_id)

    @application.post("/api/sessions/{session_id}/resume")
    async def resume(session_id: str):
        return engine.resume(session_id)

    @application.post("/api/sessions/{session_id}/continue")
    async def continue_session(session_id: str, payload: ContinueRequest):
        return engine.continue_to_next_module(session_id, payload.request_id)

    @application.post("/api/sessions/{session_id}/sync")
    async def retry_evidence_sync(session_id: str):
        return engine.retry_evidence_sync(session_id)

    @application.get("/api/dashboard")
    async def dashboard():
        return resolved_database.dashboard()

    return application


app = create_app()
