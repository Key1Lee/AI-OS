"""Consumer translations, not replacement sibling engines."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import os
from lab.adapters.bridge import invoke, project_path, ROOT, AdapterError
from .datasets import DOMAINS, injected_violations


def native_type(dtype):
    return 'BIGINT' if dtype in ('bigint','integer') else 'DECIMAL(24,6)' if dtype.startswith('numeric') else 'TIMESTAMPTZ' if dtype=='timestamptz' else 'DATE' if dtype=='date' else 'VARCHAR'


def modeling(challenge,data,actual):
    tables={}
    keys={}
    for name,records in data.items():
        t=DOMAINS[challenge.domain].table(name)
        tables[name]={'columns':{k:native_type(v) for k,v in t.columns.items()},'rows':[[json.dumps(r[k]) if isinstance(r[k],(dict,list)) else r[k] for k in t.columns] for r in records],
                      'grain_label':t.grain,'label':name,'description':t.entity}
        keys[name]=list(t.primary_key)
    # Infer transport types only; native engine assesses unique/non-null keys.
    output_types={k:('DECIMAL(24,6)' if k.endswith(('cents','seconds')) else 'BIGINT' if k in ('trips','retained','booked','capacity','completed_trips','delinquent_loans','on_hand') else 'TIMESTAMPTZ' if k in ('hour','event_at') else 'VARCHAR') for k in actual['columns']}
    output_types.update({k:'DECIMAL(24,6)' for k,v in challenge.output_types.items() if v=='numeric' and k in actual['columns']})
    tables['candidate']={'columns':output_types,'rows':[[r[k] for k in actual['columns']] for r in actual['rows']],
                         'grain_label':challenge.output_grain,'label':'candidate','description':challenge.context}
    keys['candidate']=list(challenge.output_key)
    for name in challenge.inputs:
        t=DOMAINS[challenge.domain].table(name)
        if t.natural_key!=t.primary_key:keys[name+'_natural']=list(t.natural_key);tables[name+'_natural']=tables[name]
    pairs={'fintech':('loans','payment_events','loan_id'), 'ecommerce':('order_items','refund_events','order_id'),
           'saas':('subscriptions','subscription_versions','subscription_id'), 'rides':('trips','driver_pings','driver_id'),
           'advertising':('ad_spend','conversion_credit','campaign_id'),'healthcare':('slots','appointments','slot_id')}
    joins=[]
    if challenge.id in ('FIN-001','EC-001','SAAS-003'):
        left,right,key=pairs[challenge.domain]
        joins=[{'left_table':left,'right_table':right,'left_key':key,'right_key':key,'kind':'left','expected_cardinality':'N:1','expected_rows':len(data[left])}]
    for pair in challenge.joins:
        left,right=pair.split(':');lt=DOMAINS[challenge.domain].table(left);rt=DOMAINS[challenge.domain].table(right)
        common=sorted(k for k in set(lt.columns)&set(rt.columns) if k.endswith('_id'))
        declared=[f.columns[0] for f in (*lt.foreign_keys,*rt.foreign_keys) if f.table in (left,right) and len(f.columns)==1 and f.columns==f.target]
        # Never choose a shared warehouse column arbitrarily: authorization
        # attempts and captures share both merchant_id and payment_id.
        key={'attempts:captures':'payment_id','conversions:touches':'user_id'}.get(pair)
        key=key or (declared[0] if len(set(declared))==1 else common[0] if len(common)==1 else None)
        if key and left!=right:
            joins.append({'left_table':left,'right_table':right,'left_key':key,'right_key':key,'kind':'left','expected_cardinality':'N:1','expected_rows':len(data[left])})
    return invoke('modeling',{'tables':tables,'keys':keys,'joins':joins},worker='sql_modeling.py')


def quality_columns(t):
    return [{'name':k,'data_type':'INTEGER' if v in ('bigint','integer') else 'DECIMAL' if v.startswith('numeric') else 'TIMESTAMP' if v=='timestamptz' else 'STRING',
             'nullable':k not in t.primary_key,'precision':24,'scale':6} for k,v in t.columns.items()]


def quality(challenge,data,actual,run_id):
    datasets={};contracts={}
    for name,records in data.items():
        t=DOMAINS[challenge.domain].table(name);cols=quality_columns(t)
        datasets[name]={'id':name,'columns':cols,'rows':[{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in records]}
        contracts[name]={'id':'c_'+name,'dataset_id':name,'grain':t.grain,'primary_key':list(t.primary_key),'columns':cols,
                         'owner':'AE Lab fixture producer','semantic_meaning':t.entity,
                         'relationships':[{'column':f.columns[0],'parent_dataset':f.table,'parent_column':f.target[0]} for f in t.foreign_keys if len(f.columns)==1 and not f.temporal]}
        contracts[name]['rules']=[{'id':'known_'+column,'name':'Known source monetary measure',
            'description':'Unknown source money remains visible even when the exercise KPI explicitly treats NULL as zero.',
            'target':name,'dimension':'completeness','severity':'WARNING','blocking':False,
            'expectation':{'kind':'not_null','column':column,'minimum_rate':'1'}}
            for column in t.columns if column.endswith('_cents')]
    if set(challenge.output_key)<=set(actual['columns']):
        cols=[{'name':k,'data_type':'DECIMAL' if k.endswith(('cents','seconds')) else 'INTEGER' if k in ('trips','retained','booked','capacity','completed_trips','delinquent_loans','on_hand') else 'TIMESTAMP' if k in ('hour','event_at') else 'STRING',
               'nullable':k not in challenge.output_key,'precision':24,'scale':6} for k in actual['columns']]
        for col in cols:
            if challenge.output_types.get(col['name'])=='numeric':col['data_type']='DECIMAL'
        datasets['candidate']={'id':'candidate','columns':cols,'rows':actual['rows']}
        contracts['candidate']={'id':'c_candidate','dataset_id':'candidate','grain':challenge.output_grain,'primary_key':list(challenge.output_key),'columns':cols,'owner':'AE Lab learner','semantic_meaning':challenge.context}
    stamp=datetime.now(timezone.utc).isoformat()
    return invoke('quality',{'datasets':datasets,'contracts':contracts,'run_id':run_id,'timestamp':stamp},worker='sql_quality.py')


def observe(challenge,cases,root,run_id):
    stamp=datetime.now(timezone.utc).isoformat()
    meta={'generated_at':stamp,'invocation_id':run_id,'producer':'AE SQL Lab adapter; actual PostgreSQL results, declared source→candidate lineage; no dbt execution','sample':True}
    sources={f'source.ae_sql.{name}':{'unique_id':f'source.ae_sql.{name}','name':name,'source_name':challenge.domain,'resource_type':'source','schema':'fixture','columns':{},'depends_on':{'nodes':[]},'meta':{'grain':DOMAINS[challenge.domain].table(name).grain}} for name in challenge.inputs}
    candidate='model.ae_sql.candidate';test='test.ae_sql.fixture_equivalence'
    passed=all(c['matches'] for c in cases)
    manifest={'metadata':{**meta,'dbt_schema_version':'https://schemas.getdbt.com/dbt/manifest/v12.json'},'sources':sources,'nodes':{
        candidate:{'unique_id':candidate,'name':'candidate','resource_type':'model','schema':'lab','columns':{},'depends_on':{'nodes':list(sources)},'meta':{'grain':challenge.output_grain}},
        test:{'unique_id':test,'name':'fixture_equivalence','resource_type':'test','attached_node':candidate,'columns':{},'depends_on':{'nodes':[candidate]},'test_metadata':{'name':'fixture_equivalence','kwargs':{}},'config':{'severity':'ERROR'}}},'exposures':{}}
    run_results={'metadata':{**meta,'dbt_schema_version':'https://schemas.getdbt.com/dbt/run-results/v6.json'},'results':[
        {'unique_id':candidate,'status':'success' if all(not c.get('error') for c in cases) else 'error'},
        {'unique_id':test,'status':'pass' if passed else 'fail','failures':sum(not c['matches'] for c in cases)}]}
    return invoke('observability',{'database':str(root/'sql_observability.sqlite'),'system_id':'ae-sql-'+challenge.domain,
        'manifest':manifest,'run_results':run_results},worker='sql_observability.py')


def orchestrate(run_id,rows):
    project=project_path('orchestration');tsx=project/'node_modules/.bin/tsx'
    p={'project':str(project),'run_id':run_id,'rows':rows}
    try:
        r=subprocess.run([str(tsx),str(ROOT/'lab/adapters/workers/sql_orchestration.ts')],input=json.dumps(p),capture_output=True,text=True,cwd=project,timeout=30)
    except (OSError,subprocess.TimeoutExpired) as e:raise AdapterError(str(e)) from e
    if r.returncode:raise AdapterError(r.stderr[-2000:])
    return json.loads(r.stdout)


def semantic_reference():
    # Semantic owns a stdlib-only SDK; an isolated consumer worker uses Lab Python
    # when this sibling has no virtualenv. No catalog or approval is written.
    return invoke('semantic',{},worker='sql_semantic.py')
