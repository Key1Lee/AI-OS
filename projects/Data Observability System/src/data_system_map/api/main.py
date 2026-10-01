from pathlib import Path
from threading import Lock
import secrets
import logging
import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from data_system_map import create_service
from data_system_map.config import Settings
from .boundary import install_local_boundary, install_map_errors
from .context import MapContext
from .router import mount_map_routes


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    application = FastAPI(title='Data Observability System',version='0.1.0',docs_url=None,redoc_url=None,openapi_url='/api/openapi.json')
    token = secrets.token_urlsafe(32)
    install_local_boundary(application,token)
    install_map_errors(application)
    lock = Lock()

    def runtime(request: Request):
        with lock:
            if not hasattr(application.state,'data_map'):
                try:
                    application.state.data_map = MapContext(create_service(settings.database_path,seed_demo=True))
                except (ValueError,sqlite3.Error,OSError):
                    logging.getLogger(__name__).error('{"event":"map_initialization_failed"}')
                    raise HTTPException(503,'Data System Map storage or its sample artifacts are unavailable.') from None
        return application.state.data_map

    @application.exception_handler(KeyError)
    async def missing(_,exc):
        return JSONResponse(status_code=404,content={'detail':'Resource not found.'})

    @application.get('/api/config')
    def config():
        return {'request_token':token,'ai_available':False}

    @application.get('/api/health')
    def health():
        return {'status':'ok','service':'data-observability-system'}

    mount_map_routes(application,runtime)
    static = settings.web_dist
    if (static/'assets').exists():
        application.mount('/assets',StaticFiles(directory=static/'assets'),name='assets')

    @application.get('/',include_in_schema=False)
    @application.get('/map',include_in_schema=False)
    def index():
        if not (static/'index.html').exists():
            raise HTTPException(503,'Build the local UI using make setup, then restart observability.')
        return FileResponse(static/'index.html')

    return application
