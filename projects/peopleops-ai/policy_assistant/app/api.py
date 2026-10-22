from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.config import Settings
from app.contracts import Answer, IngestRequest, Question
from app.providers import Providers
from app.security import authenticate, require_admin, safety_response
from app.service import ask_policy
from app.storage import VersionConflict, connect, ingest
from app.middleware import RequestSizeLimit


def create_app(settings=None, providers=None):
    """Wire small policy functions into authenticated HTTP routes and serve the chat page."""
    settings = settings or Settings()
    providers = providers or Providers(settings)
    credentials = settings.credentials()
    app = FastAPI(title="PeopleOps AI · fictional policy assistant", version="1.0.0")
    app.add_middleware(RequestSizeLimit, max_bytes=512_000)

    def identity(authorization: str | None = Header(default=None)):
        return authenticate(authorization, credentials)

    def admin(actor=Depends(identity)):
        return require_admin(actor)

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo request bodies, which may contain accidentally pasted personal data.
        return JSONResponse(status_code=422, content={"detail": "Invalid request fields or values"})

    @app.exception_handler(psycopg.Error)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={"detail": "Policy storage is unavailable"})

    @app.get("/me")
    def me(actor=Depends(identity)):
        return {"identity": actor, "mode": f"LLM: {settings.llm_provider} · embeddings: {settings.embedding_provider}"}

    @app.get("/health")
    @app.get("/admin/health")
    def health(actor=Depends(admin)):
        with connect(settings) as conn:
            conn.execute("SELECT 1 FROM policy_documents LIMIT 1")
        return {"status": "ok", "database": "ready", "llm_provider": settings.llm_provider,
                "embedding_provider": settings.embedding_provider}

    @app.post("/admin/ingest")
    def ingest_documents(body: IngestRequest, actor=Depends(admin)):
        try:
            with connect(settings) as conn:
                result = ingest(conn, body.documents, actor, providers, settings)
            return {"documents": result}
        except VersionConflict as error:
            raise HTTPException(409, str(error)) from error
        except (ValueError, TypeError, yaml.YAMLError) as error:
            raise HTTPException(422, "Invalid policy metadata, content, or embeddings") from error
        except (httpx.HTTPError, KeyError, IndexError) as error:
            raise HTTPException(503, "Embedding provider is unavailable") from error

    @app.post("/ask", response_model=Answer)
    def ask(body: Question, actor=Depends(identity)):
        request_id = str(uuid4())
        try:
            answer = safety_response(body.question)
            if answer is None:
                with connect(settings) as conn:
                    answer = ask_policy(conn, body.question, actor, providers, settings)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            answer = Answer(status="unavailable", answer="The policy provider is unavailable or returned invalid evidence. Please try again or contact People Operations.")
        answer.request_id = request_id
        answer.mode = f"LLM: {settings.llm_provider} · embeddings: {settings.embedding_provider}"
        return answer

    @app.post("/chat", response_model=Answer)
    async def chat(body: Question, actor=Depends(identity), authorization: str = Header()):
        """Send the chat message through n8n with the caller's token. n8n forwards it to /ask and returns the same structured response."""
        try:
            async with httpx.AsyncClient(timeout=50, follow_redirects=False) as client:
                response = await client.post(settings.n8n_webhook_url, headers={"Authorization": authorization}, json=body.model_dump())
                if response.status_code in (401, 403, 422, 503):
                    raise HTTPException(response.status_code, "The workflow could not complete the request")
                response.raise_for_status()
                return Answer.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise HTTPException(503, "The chat workflow is unavailable; retry or use POST /ask") from error

    static = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(static / "index.html")

    return app


app = create_app()
