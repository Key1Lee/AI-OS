import logging
import secrets
import sqlite3
from urllib.parse import urlsplit
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from starlette.middleware.trustedhost import TrustedHostMiddleware
from data_system_map import ArtifactError


def install_local_boundary(application, token, *, token_header='X-Observability-Token'):
    application.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
    @application.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST","PUT","PATCH","DELETE"}:
            origin = request.headers.get("origin")
            if origin and (urlsplit(origin).netloc != request.url.netloc or urlsplit(origin).scheme != request.url.scheme):
                return JSONResponse(status_code=403,content={"detail":"Mutation requests must come from this local application."})
            if not secrets.compare_digest(request.headers.get(token_header.lower(), ""),token):
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

def install_map_errors(application):
    @application.exception_handler(ArtifactError)
    async def artifact_error(_,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422,content={'detail':str(exc)})

    @application.exception_handler(sqlite3.Error)
    async def metadata_failure(_,exc):
        from fastapi.responses import JSONResponse
        logging.getLogger(__name__).error('{"event":"map_storage_failed"}')
        return JSONResponse(status_code=503,content={'detail':'Map storage is unavailable. Your browser notes are retained; retry after restoring the profile.'})
