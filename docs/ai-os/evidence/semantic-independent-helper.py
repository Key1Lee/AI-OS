import copy, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path('/Users/key/_AI-OS/projects/Semantic & Metrics System')
sys.path.insert(0,str(ROOT))
from semantic.core import Registry, SemanticError, evaluate, load_catalog, load_snapshot

def request(metric='net_revenue', consumer='api', **changes):
    r={'contract_version':'semantic-query-v1','metric_id':metric,'version':'1.0.0','consumer':consumer,'start':'2026-09-30','end':'2026-10-02','dimensions':[]};r.update(changes);return r
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'semantic/data').glob('*.json')}
count=0
with tempfile.TemporaryDirectory(prefix='sem-independent-') as tmp:
    def cli(*args,success=True):
        global count
        count+=1
        p=subprocess.run([sys.executable,'-m','semantic',*args],cwd=ROOT,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        assert (p.returncode==0)==success,(args,p.returncode,p.stderr)
        return p.stdout
    def scenario(*args,success=True): return cli('scenario','SEM-REVENUE-001',*args,'--state-dir',tmp,success=success)
    opening=scenario()
    assert all(x not in opening for x in ('SUM(','gross_order_value','fulfilled_at','net_revenue','semantic drift'))
    scenario('inspect','--artifact','finance-owner',success=False)
    scenario('predict','--text','I would inspect health, row meaning, and report contracts before claiming a data fault.')
    health=json.loads(scenario('inspect','--artifact','health'))
    assert 'SUM(' not in health['content']
    scenario('inspect','--artifact','finance-owner',success=False)
    for artifact in ('models','data','dashboard-a','dashboard-b','finance-owner','time-policy','identity-policy'): scenario('inspect','--artifact',artifact)
    scenario('diagnose','--text','The two report formulas differ; the owner must choose a definition for this decision. Technical checks do not decide the meaning.')
    draft=json.loads(scenario('template'));assert draft['formula']==draft['time_dimension']==draft['timezone']=='' and draft['measure']==[]
    proposal=Registry().get('net_revenue','1.0.0');proposal.update(status='PROPOSED',approval=None)
    bad=copy.deepcopy(proposal);bad['business_definition']='Gross revenue before refunds; do not reduce revenue by refunds.'
    path=Path(tmp)/'proposal.json';path.write_text(json.dumps(bad))
    scenario('propose','--contract',str(path),success=False)
    assert json.loads(scenario('status'))['stage']=='DESIGN'
    path.write_text(json.dumps(proposal));scenario('propose','--contract',str(path));scenario('apply')
    report=json.loads(scenario('verify'));assert report['status']=='PASS' and report['practice_assessment']=='unassessed'
    assert {r['rows'][0]['integer_value'] for r in report['consumers']}=={820000000}
    assert len({r['definition_fingerprint'] for r in report['consumers']})==1
    assert len({r['catalog_fingerprint'] for r in report['consumers']})==1
    scenario('recall','--text','Test fixture recall remains unassessed; this is not a learner attempt.')
    assert json.loads(scenario('status'))['stage']=='TRANSFER_PENDING'
    assert json.loads(scenario('status'))['assessment']=='unassessed_practice'
registry=Registry();snapshot=load_snapshot();guards={}
def reject(name, r=None,s=None,c=None):
    try: evaluate(Registry(c) if c else registry,s or snapshot,r or request())
    except SemanticError: guards[name]='REJECTED';return
    raise AssertionError(name+' did not reject')
for asset in ('fct_orders','fct_order_refunds','dim_customers','dim_products'):
    s=copy.deepcopy(snapshot);s['tables'][asset]['rows'].append(copy.deepcopy(s['tables'][asset]['rows'][0]));reject('duplicate-'+asset,s=s)
for field in ('formula','sql','business_definition','time_dimension'):reject('consumer-'+field,r=request(**{field:'redefine'}))
reject('unsupported-customer-dimension',r=request('active_customers',dimensions=['product_category']))
c=load_catalog();c['measures']['gross_order_value']['field']='refund_amount_cents';reject('measure-binding',c=c)
s=load_snapshot();s['tables']['fct_orders']['rows'][0]['gross_order_value_cents']=9007199254740993;s['tables']['fct_orders']['rows'][1]['gross_order_value_cents']=0
huge=evaluate(registry,s,request('gross_revenue'))['rows'][0];assert huge['value']=='90071992547409.93' and huge['integer_value']==9007199254740993
rows=evaluate(registry,snapshot,request(dimensions=['date']))['rows'];assert rows[0]['date']=='2026-09-30' and rows[0]['integer_value']==380000000
all_results=[evaluate(registry,snapshot,request(consumer=c)) for c in ('dashboard_a','dashboard_b','api','ai','sql')]
assert all(r['rows']==all_results[0]['rows'] and r['definition_fingerprint']==all_results[0]['definition_fingerprint'] for r in all_results)
after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'semantic/data').glob('*.json')};assert before==after
print(json.dumps({'result':'PASS','cli_commands':count,'adversarial_guards':guards,'consumer_count':len(all_results),'net_revenue_cents':820000000,'large_amount_exact':huge['value'],'chicago_boundary':'2026-09-30','scenario_end':'TRANSFER_PENDING','practice':'unassessed','bundled_data_unchanged':before==after},sort_keys=True))
