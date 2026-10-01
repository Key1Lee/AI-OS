from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from data_system_map.adapters.dbt import ArtifactError
from data_system_map.graph import Graph
from data_system_map.repository import MetadataStore
from data_system_map.security import redact
from data_system_map.service import DataSystemService
from trainer.config import ROOT, Settings
from trainer.data_map.service import InvestigationService
from trainer.data_map.store import InvestigationStore, MapConflict


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ImportRequest(StrictRequest):
    system_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')
    name: str = Field(min_length=1,max_length=150)
    manifest: dict
    run_results: dict | None = None
    catalog: dict | None = None
    freshness: dict | None = None


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


class GraphQuery(StrictRequest):
    operation: Literal['get_node','upstream','downstream','direct_parents','direct_children','impact','shortest_path','all_paths','column_lineage','failed_path','affected_outputs','changed_nodes']
    node_id: str | None = Field(default=None,max_length=256)
    start: str | None = Field(default=None,max_length=256)
    end: str | None = Field(default=None,max_length=256)
    column: str | None = Field(default=None,max_length=256)


class InvestigationQuery(StrictRequest):
    system_id: str
    node_id: str


class Runtime:
    def __init__(self, settings: Settings):
        parent = settings.database_path.parent
        normal = settings.database_path == ROOT/'data/ae-trainer.db'
        metadata_path = parent/('data-system-map.db' if normal else 'data-map-'+settings.database_path.stem+'.db')
        training_path = parent/('data-map-training.db' if normal else 'map-actions-'+settings.database_path.stem+'.db')
        self.engine = DataSystemService(MetadataStore(metadata_path))
        self.training = InvestigationService(InvestigationStore(training_path),self.engine)
        if not any(s['id']=='commerce-demo' for s in self.engine.store.systems()):
            directory = ROOT/'fixtures/data-map/commerce'
            artifacts = {name:json.loads((directory/name).read_text()) for name in ['manifest.json','run_results.json','catalog.json','sources.json']}
            self.engine.import_dbt('commerce-demo','Commerce revenue pipeline',artifacts['manifest.json'],run_results=artifacts['run_results.json'],catalog=artifacts['catalog.json'],freshness=artifacts['sources.json'])

    def policy(self, system_id):
        return self.training.policy(system_id)

    def action(self, system_id, kind, target=None, payload=None):
        return self.training.action(system_id,kind,target,payload)


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

    def node_view(r,system_id,key,kind='node'):
        policy = r.policy(system_id)
        value = r.engine.node(system_id,key,snapshot_id=policy['snapshot_id'],reveal_diagnostics=policy['reveal_diagnostics'])
        r.action(system_id,kind,key)
        value['sql_available'] = value['sql'] is not None or value['compiled_sql'] is not None
        value.pop('sql')
        value.pop('compiled_sql')
        return value

    @application.exception_handler(MapConflict)
    async def map_conflict(_,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409,content={'detail':str(exc)})

    @application.exception_handler(ArtifactError)
    async def artifact_error(_,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422,content={'detail':str(exc)})

    @application.exception_handler(sqlite3.Error)
    async def metadata_failure(_,exc):
        from fastapi.responses import JSONResponse
        logging.getLogger(__name__).error('{"event":"map_storage_failed"}')
        return JSONResponse(status_code=503,content={'detail':'Map storage is unavailable. Your browser notes are retained; retry after restoring the profile.'})

    @router.get('/systems')
    def systems(r:Runtime=Depends(runtime)):
        return r.engine.store.systems()

    @router.post('/systems/import',status_code=201)
    def import_system(payload:ImportRequest,r:Runtime=Depends(runtime)):
        current = r.training.current()
        if current and current['mode']=='assessment':
            raise MapConflict('End the active assessment before importing another graph.')
        if payload.system_id=='commerce-demo':
            raise MapConflict('The authored commerce demonstration is reserved. Import your artifacts under a different system ID.')
        try:
            snapshot = r.engine.import_dbt(**payload.model_dump())
        except ValueError as exc:
            if isinstance(exc,ArtifactError):
                raise
            raise HTTPException(422,'Artifact normalization failed validation. The previous graph was preserved.') from None
        return {'system_id':snapshot.system_id,'snapshot_id':snapshot.snapshot_id,'nodes':len(snapshot.nodes),'edges':len(snapshot.edges),'issues':[i.model_dump() for i in snapshot.issues]}

    @router.get('/systems/{system_id}/graph')
    def graph(system_id:str,level:Literal['overview','models']='overview',focus:str|None=None,layer:str|None=None,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        result = r.engine.graph(system_id,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'],level=level,focus=focus,layer=layer)
        if focus or layer:
            r.action(system_id,'lineage' if focus else 'stage',focus,{'layer':layer})
        result['audience'] = p['audience']
        return result

    @router.get('/systems/{system_id}/search')
    def search(system_id:str,q:str='',r:Runtime=Depends(runtime)):
        if len(q)>300:
            raise HTTPException(422,'Search text is too long.')
        p = r.policy(system_id)
        snapshot = r.engine.snapshot(system_id,p['snapshot_id'])
        term = q.strip().casefold()
        matches = [{'id':n.id,'name':n.name,'columns':[c.name for c in n.columns if term in c.name.casefold()]} for n in snapshot.nodes
                   if n.node_type!='test' and term and (term in n.name.casefold() or term in (n.description or '').casefold() or any(term in c.name.casefold() for c in n.columns))]
        if term:
            r.action(system_id,'search',payload={'term':redact(q)})
        return {'matches':matches[:100],'truncated':len(matches)>100,'query_type':'metadata_search','message':'Search matches names, descriptions and columns; it does not infer relationships.'}

    @router.get('/systems/{system_id}/nodes/{key}')
    def node(system_id:str,key:str,r:Runtime=Depends(runtime)):
        return node_view(r,system_id,key)

    @router.get('/systems/{system_id}/nodes/{key}/schema')
    def schema(system_id:str,key:str,r:Runtime=Depends(runtime)):
        value = node_view(r,system_id,key,'schema')
        return {'node_id':key,'columns':value['columns'],'grain':value['grain'],'primary_keys':value['primary_keys'],'classification':'FACT','basis':'Declared metadata and optional catalog schema.'}

    @router.get('/systems/{system_id}/nodes/{key}/tests')
    def tests(system_id:str,key:str,r:Runtime=Depends(runtime)):
        return {'node_id':key,'tests':node_view(r,system_id,key,'tests')['tests'],'executed_now':False,'message':'Recorded artifact results; no dbt command was executed.'}

    @router.get('/systems/{system_id}/nodes/{key}/sql')
    def sql(system_id:str,key:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = r.engine.node(system_id,key,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        r.action(system_id,'sql',key)
        return {'node_id':key,'sql':value['sql'],'compiled_sql':value['compiled_sql'],'classification':'FACT','executed':False,'provenance':value['provenance']}

    @router.get('/systems/{system_id}/nodes/{key}/upstream')
    def upstream(system_id:str,key:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = r.engine.relation(system_id,key,'upstream',snapshot_id=p['snapshot_id'])
        r.action(system_id,'upstream',key)
        return value

    @router.get('/systems/{system_id}/nodes/{key}/downstream')
    def downstream(system_id:str,key:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = r.engine.relation(system_id,key,'downstream',snapshot_id=p['snapshot_id'])
        r.action(system_id,'downstream',key)
        return value

    @router.get('/systems/{system_id}/nodes/{key}/impact')
    def impact(system_id:str,key:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = r.engine.impact(system_id,key,snapshot_id=p['snapshot_id'])
        r.action(system_id,'impact',key)
        return {'node_id':key,**value,'classification':'FACT','basis':'Declared dependencies; impacted outputs may require validation, not automatic proof of wrong values.'}

    @router.get('/systems/{system_id}/nodes/{key}/columns/{column}/lineage')
    def column_lineage(system_id:str,key:str,column:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = Graph(r.engine.snapshot(system_id,p['snapshot_id'])).column_lineage(key,column)
        r.action(system_id,'column_lineage',key,{'column':column})
        return value

    @router.get('/systems/{system_id}/incidents')
    def incidents(system_id:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        return r.engine.incidents(system_id,snapshot_id=p['snapshot_id'])

    def failure_view(r,system_id,key):
        p = r.policy(system_id)
        try:
            value = r.engine.investigate(system_id,key,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        except ValueError:
            raise HTTPException(422,'This node has no recorded execution or test failure. Inspect its node evidence instead.') from None
        r.action(system_id,'failure_path',key)
        return value

    @router.get('/systems/{system_id}/incidents/{key}')
    def incident(system_id:str,key:str,r:Runtime=Depends(runtime)):
        return failure_view(r,system_id,key)

    @router.post('/debug/investigate')
    def investigate(payload:InvestigationQuery,r:Runtime=Depends(runtime)):
        return failure_view(r,payload.system_id,payload.node_id)

    @router.get('/systems/{system_id}/explain')
    def explain(system_id:str,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        value = r.engine.explain(system_id,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        if p['audience']=='assessment':
            raise MapConflict('Guided explanations are disabled during assessment. Inspect the evidence through your own actions.')
        r.action(system_id,'system_tour')
        return value

    @router.post('/systems/{system_id}/query')
    def query(system_id:str,payload:GraphQuery,r:Runtime=Depends(runtime)):
        p = r.policy(system_id)
        g = Graph(r.engine.snapshot(system_id,p['snapshot_id']))
        op,key = payload.operation,payload.node_id
        if op in {'shortest_path','all_paths'}:
            if not payload.start or not payload.end:
                raise HTTPException(422,'A path query requires start and end nodes.')
            result = {'path':g.shortest_path(payload.start,payload.end)} if op=='shortest_path' else g.all_paths(payload.start,payload.end)
            r.action(system_id,'path',payload.start,{'end':payload.end})
            return result
        if op=='changed_nodes':
            return r.engine.changed_nodes(system_id,snapshot_id=p['snapshot_id'],key=key)
        if not key:
            raise HTTPException(422,'This graph operation requires node_id.')
        if op=='get_node':
            return node_view(r,system_id,key)
        if op=='failed_path':
            return failure_view(r,system_id,key)
        if op in {'upstream','downstream'}:
            value = r.engine.relation(system_id,key,op,snapshot_id=p['snapshot_id'])
        elif op in {'impact','affected_outputs'}:
            value = r.engine.impact(system_id,key,snapshot_id=p['snapshot_id'])
            if op=='affected_outputs':
                value = {'affected_outputs':value['affected_outputs']}
        elif op=='column_lineage':
            if not payload.column:
                raise HTTPException(422,'Column lineage requires a column name.')
            value = g.column_lineage(key,payload.column)
        else:
            value = {'node_ids':g.direct_parents(key) if op=='direct_parents' else g.direct_children(key)}
        r.action(system_id,op,key)
        return value

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
