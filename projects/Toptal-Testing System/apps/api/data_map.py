from __future__ import annotations
import logging
import re
import sqlite3
from threading import Lock
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator
from data_system_map import create_service, redact
from data_system_map.api.context import MapContext
from data_system_map.api.contracts import StrictRequest
from data_system_map.api.router import mount_map_routes
from data_system_map.api.boundary import install_map_errors
from data_system_map.config import Settings as ObservabilitySettings
from trainer.config import ROOT, Settings
from trainer.data_map.service import InvestigationService
from trainer.data_map.store import InvestigationStore, MapConflict


class StartInvestigation(StrictRequest):
    system_id: str
    mode: Literal['learning','assessment']


class Answer(StrictRequest):
    observed_failure: str = Field(default='',max_length=256)
    suspected_origin: str = Field(default='',max_length=256)
    grain: Literal['','one_row_per_order','one_row_per_item','unknown'] = ''
    affected_outputs: list[str] = Field(default_factory=list,max_length=50)
    fix_proposal: str = Field(default='',max_length=12000)
    verification_plan: str = Field(default='',max_length=12000)
    notes: str = Field(default='',max_length=12000)

    @field_validator('observed_failure','suspected_origin','affected_outputs')
    @classmethod
    def selection_ids(cls,value):
        values = value if isinstance(value,list) else [value]
        for item in values:
            if (item or isinstance(value,list)) and (not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:-]{0,255}',item) or redact(item)!=item):
                raise ValueError('Select a valid resource identity.')
        return value

    @field_validator('fix_proposal','verification_plan','notes')
    @classmethod
    def redact_text(cls,value):
        return redact(value)


class Draft(Answer):
    revision: int = Field(ge=0)


class Diagnosis(Answer):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{8,128}$')

    @field_validator('request_id')
    @classmethod
    def safe_request_id(cls,value):
        if redact(value)!=value:
            raise ValueError('Request identities must not contain secret patterns.')
        return value


class Hypothesis(StrictRequest):
    text: str = Field(min_length=1,max_length=4000)


class EndRequest(StrictRequest):
    learn: bool = False


class Runtime(MapContext):
    def __init__(self, settings: Settings):
        parent = settings.database_path.parent
        normal = settings.database_path == ROOT/'data/ae-trainer.db'
        generic_root = ROOT.parent/'Data Observability System'
        metadata_path = (ObservabilitySettings.from_env(root=generic_root).database_path if normal else
                         parent/('data-map-'+settings.database_path.stem+'.db'))
        training_path = parent/('data-map-training.db' if normal else 'map-actions-'+settings.database_path.stem+'.db')
        super().__init__(create_service(metadata_path,seed_demo=True))
        self.training = InvestigationService(InvestigationStore(training_path),self.engine)

    def view_options(self, system_id):
        return self.training.policy(system_id)

    def action(self, system_id, kind, target=None, payload=None):
        return self.training.action(system_id,kind,target,payload)

    def ensure_import_allowed(self, system_id):
        current = self.training.current()
        if current and current['mode']=='assessment':
            raise MapConflict('End the active assessment before importing another graph.')
        if system_id=='commerce-demo':
            raise MapConflict('The authored commerce demonstration is reserved. Import your artifacts under a different system ID.')

    def require_explanation(self, system_id):
        if self.view_options(system_id)['audience']=='assessment':
            raise MapConflict('Guided explanations are disabled during assessment. Inspect the evidence through your own actions.')

    def project_incident(self, value, options):
        if not options['reveal_diagnostics']:
            value['message'] = 'Assessment-safe failure view. Inspect nodes and recorded tests to gather evidence. No automatic cause or investigation hint is supplied.'
        return value


def mount_data_map(application, settings):
    router = APIRouter(prefix='/api/map')
    lock = Lock()

    def runtime(request: Request):
        with lock:
            if not hasattr(application.state,'data_map'):
                try:
                    application.state.data_map = Runtime(settings)
                except (ValueError,sqlite3.Error,OSError):
                    logging.getLogger(__name__).error('{"event":"map_initialization_failed"}')
                    raise HTTPException(503,'Data System Map storage or its sample artifacts are unavailable. Existing training records were not changed.') from None
        return application.state.data_map

    install_map_errors(application)
    mount_map_routes(application,runtime)

    @application.exception_handler(MapConflict)
    async def map_conflict(_,exc):
        return JSONResponse(status_code=409,content={'detail':str(exc)})

    @router.get('/investigations/current')
    def current(r:Runtime=Depends(runtime)):
        return r.training.current()

    @router.get('/investigations/history')
    def history(r:Runtime=Depends(runtime)):
        return r.training.history()

    @router.post('/investigations',status_code=201)
    def start(payload:StartInvestigation,r:Runtime=Depends(runtime)):
        return r.training.start(payload.system_id,payload.mode)

    @router.get('/investigations/{key}')
    def saved(key:str,r:Runtime=Depends(runtime)):
        return r.training.get(key)

    @router.put('/investigations/{key}/draft')
    def draft(key:str,payload:Draft,r:Runtime=Depends(runtime)):
        return r.training.save(key,payload.model_dump(exclude={'revision'}),payload.revision)

    @router.post('/investigations/{key}/hypotheses')
    def hypothesis(key:str,payload:Hypothesis,r:Runtime=Depends(runtime)):
        return r.training.hypothesis(key,payload.text)

    @router.post('/investigations/{key}/submit')
    def submit(key:str,payload:Diagnosis,r:Runtime=Depends(runtime)):
        return r.training.submit(key,payload.model_dump())

    @router.post('/investigations/{key}/end')
    def end(key:str,payload:EndRequest,r:Runtime=Depends(runtime)):
        return r.training.end(key,learn=payload.learn)

    application.include_router(router)
