from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from data_system_map import ArtifactError, redact
from .context import MapContext
from .contracts import ImportRequest, GraphQuery, InvestigationQuery


def mount_map_routes(application, runtime):
    router = APIRouter(prefix='/api/map')
    def node_view(r,system_id,key,kind='node'):
        policy = r.view_options(system_id)
        value = r.engine.node(system_id,key,snapshot_id=policy['snapshot_id'],reveal_diagnostics=policy['reveal_diagnostics'])
        r.action(system_id,kind,key)
        value['sql_available'] = value['sql'] is not None or value['compiled_sql'] is not None
        value.pop('sql')
        value.pop('compiled_sql')
        return value

    @router.get('/systems')
    def systems(r:MapContext=Depends(runtime)):
        return r.engine.systems()

    @router.post('/systems/import',status_code=201)
    def import_system(payload:ImportRequest,r:MapContext=Depends(runtime)):
        r.ensure_import_allowed(payload.system_id)
        try:
            snapshot = r.engine.import_dbt(**payload.model_dump())
        except ValueError as exc:
            if isinstance(exc,ArtifactError):
                raise
            raise HTTPException(422,'Artifact normalization failed validation. The previous graph was preserved.') from None
        return {'system_id':snapshot.system_id,'snapshot_id':snapshot.snapshot_id,'nodes':len(snapshot.nodes),'edges':len(snapshot.edges),'issues':[i.model_dump() for i in snapshot.issues]}

    @router.get('/systems/{system_id}/graph')
    def graph(system_id:str,level:Literal['overview','models']='overview',focus:str|None=None,layer:str|None=None,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        result = r.engine.graph(system_id,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'],level=level,focus=focus,layer=layer)
        if focus or layer:
            r.action(system_id,'lineage' if focus else 'stage',focus,{'layer':layer})
        result['audience'] = p['audience']
        return result

    @router.get('/systems/{system_id}/search')
    def search(system_id:str,q:str='',r:MapContext=Depends(runtime)):
        if len(q)>300:
            raise HTTPException(422,'Search text is too long.')
        p = r.view_options(system_id)
        snapshot = r.engine.snapshot(system_id,p['snapshot_id'])
        term = q.strip().casefold()
        matches = [{'id':n.id,'name':n.name,'columns':[c.name for c in n.columns if term in c.name.casefold()]} for n in snapshot.nodes
                   if n.node_type!='test' and term and (term in n.name.casefold() or term in (n.description or '').casefold() or any(term in c.name.casefold() for c in n.columns))]
        if term:
            r.action(system_id,'search',payload={'term':redact(q)})
        return {'matches':matches[:100],'truncated':len(matches)>100,'query_type':'metadata_search','message':'Search matches names, descriptions and columns; it does not infer relationships.'}

    @router.get('/systems/{system_id}/nodes/{key}')
    def node(system_id:str,key:str,r:MapContext=Depends(runtime)):
        return node_view(r,system_id,key)

    @router.get('/systems/{system_id}/nodes/{key}/schema')
    def schema(system_id:str,key:str,r:MapContext=Depends(runtime)):
        value = node_view(r,system_id,key,'schema')
        return {'node_id':key,'columns':value['columns'],'grain':value['grain'],'primary_keys':value['primary_keys'],'classification':'FACT','basis':'Declared metadata and optional catalog schema.'}

    @router.get('/systems/{system_id}/nodes/{key}/tests')
    def tests(system_id:str,key:str,r:MapContext=Depends(runtime)):
        return {'node_id':key,'tests':node_view(r,system_id,key,'tests')['tests'],'executed_now':False,'message':'Recorded artifact results; no dbt command was executed.'}

    @router.get('/systems/{system_id}/nodes/{key}/sql')
    def sql(system_id:str,key:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.node(system_id,key,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        r.action(system_id,'sql',key)
        return {'node_id':key,'sql':value['sql'],'compiled_sql':value['compiled_sql'],'classification':'FACT','executed':False,'provenance':value['provenance']}

    @router.get('/systems/{system_id}/nodes/{key}/upstream')
    def upstream(system_id:str,key:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.relation(system_id,key,'upstream',snapshot_id=p['snapshot_id'])
        r.action(system_id,'upstream',key)
        return value

    @router.get('/systems/{system_id}/nodes/{key}/downstream')
    def downstream(system_id:str,key:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.relation(system_id,key,'downstream',snapshot_id=p['snapshot_id'])
        r.action(system_id,'downstream',key)
        return value

    @router.get('/systems/{system_id}/nodes/{key}/impact')
    def impact(system_id:str,key:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.impact(system_id,key,snapshot_id=p['snapshot_id'])
        r.action(system_id,'impact',key)
        return {'node_id':key,**value,'classification':'FACT','basis':'Declared dependencies; impacted outputs may require validation, not automatic proof of wrong values.'}

    @router.get('/systems/{system_id}/nodes/{key}/columns/{column}/lineage')
    def column_lineage(system_id:str,key:str,column:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.query(system_id,'column_lineage',snapshot_id=p['snapshot_id'],node_id=key,column=column)
        r.action(system_id,'column_lineage',key,{'column':column})
        return value

    @router.get('/systems/{system_id}/incidents')
    def incidents(system_id:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        return r.engine.incidents(system_id,snapshot_id=p['snapshot_id'])

    def failure_view(r,system_id,key):
        p = r.view_options(system_id)
        try:
            value = r.engine.investigate(system_id,key,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        except ValueError:
            raise HTTPException(422,'This node has no recorded execution or test failure. Inspect its node evidence instead.') from None
        r.action(system_id,'failure_path',key)
        return r.project_incident(value,p)

    @router.get('/systems/{system_id}/incidents/{key}')
    def incident(system_id:str,key:str,r:MapContext=Depends(runtime)):
        return failure_view(r,system_id,key)

    @router.post('/debug/investigate')
    def investigate(payload:InvestigationQuery,r:MapContext=Depends(runtime)):
        return failure_view(r,payload.system_id,payload.node_id)

    @router.get('/systems/{system_id}/explain')
    def explain(system_id:str,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        value = r.engine.explain(system_id,snapshot_id=p['snapshot_id'],reveal_diagnostics=p['reveal_diagnostics'])
        r.require_explanation(system_id)
        r.action(system_id,'system_tour')
        return value

    @router.post('/systems/{system_id}/query')
    def query(system_id:str,payload:GraphQuery,r:MapContext=Depends(runtime)):
        p = r.view_options(system_id)
        op,key = payload.operation,payload.node_id
        if op in {'shortest_path','all_paths'}:
            if not payload.start or not payload.end:
                raise HTTPException(422,'A path query requires start and end nodes.')
            result = r.engine.query(system_id,op,snapshot_id=p['snapshot_id'],start=payload.start,end=payload.end)
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
            value = r.engine.query(system_id,op,snapshot_id=p['snapshot_id'],node_id=key,column=payload.column)
        else:
            value = r.engine.query(system_id,op,snapshot_id=p['snapshot_id'],node_id=key)
        r.action(system_id,op,key)
        return value

    application.include_router(router)
