import sys, json, os, tempfile, subprocess
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'/Users/key/_AI-OS')
from pydantic import BaseModel
from py_dev.config import ModelSettings
from py_dev.providers.parsed import ParsedModelClient
from py_dev.providers import ProviderUnavailable
from py_dev.models import ModelRequest
helper_path = Path(__file__).with_name('aios-independent-helper.py')
exec(compile(helper_path.read_text().split('checks=[]')[0],str(helper_path),'exec'))
class Answer(BaseModel): value:int
class SessionError(Exception): status_code=404
results=[]
with tempfile.TemporaryDirectory(prefix='aios-recovery-') as temp:
 root=Path(temp)
 for budget in [1,2]:
  calls=[]; events=[]
  def parse(**kwargs):
   calls.append(kwargs)
   if len(calls)==1: raise SessionError('safe diagnostic')
   return SimpleNamespace(output_parsed=Answer(value=42),id='resp-new',model='openai-test',usage=None)
  settings=ModelSettings(openai_enabled=True,openai_model='openai-test',cloud_call_budget=budget,cloud_budget_file=root/f'budget-{budget}.json',audit_file=root/f'audit-{budget}.jsonl')
  client=ParsedModelClient('openai','openai-test',calling_system='helper',client=SimpleNamespace(responses=SimpleNamespace(parse=parse)),settings=settings,event_sink=events.append)
  status='proposed'
  try: out=client.parse(output_type=Answer,instructions='prompt-secret-marker',context={'private':'state-secret-marker'},run_id='recovery-run',request_id=f'recovery-{budget}',previous_response_id='missing',store=True)
  except ProviderUnavailable: status='unavailable'
  audit=[json.loads(line) for line in settings.audit_file.read_text().splitlines()]
  assert len(calls)==budget and json.loads(settings.cloud_budget_file.read_text())['used']==budget
  assert 'previous_response_id' in calls[0] and (len(calls)==1 or 'previous_response_id' not in calls[1])
  assert (status=='proposed')==(budget==2)
  assert audit[0]['response_status']=='session_recovery_failed' and events[0]['status']=='session_recovery_failed'
  assert all(e['request_id']==f'recovery-{budget}' and e['run_id']=='recovery-run' and e['calling_system']=='helper' for e in audit+events)
  raw=json.dumps(audit+events); assert 'prompt-secret-marker' not in raw and 'state-secret-marker' not in raw
  results.append({'case':'session_recovery','daily_budget':budget,'physical_sdk_calls':len(calls),'reservations':budget,'model_audit_statuses':[e['response_status'] for e in audit],'event_statuses':[e['status'] for e in events],'outcome':status})
 for limits in [{'max_cloud_calls':1},{'max_provider_attempts':1}]:
  service,providers,events=harness([result()],claude=[result(model='claude-test')])
  out=service.router.run(ModelRequest(({'role':'user','content':'answer'},),brain='openai',review_with='claude',**limits))
  assert not out.degraded and out.review.degraded and len(providers['openai'].calls)==1 and not providers['claude'].calls
  results.append({'case':'review_hard_limit','limits':limits,'primary_calls':1,'review_calls':0,'review_status':'unavailable'})
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',AI_OS_PROVIDER_QWEN_ENABLED='false',AI_OS_PROVIDER_OPENAI_ENABLED='false',AI_OS_PROVIDER_CLAUDE_ENABLED='false',AI_OS_PROVIDER_JEV_ENABLED='false',AI_OS_EVENT_FILE=str(root/'events.jsonl'),MODEL_AUDIT_FILE=str(root/'models.jsonl'),CLOUD_BUDGET_FILE=str(root/'cli-budget.json'))
 payloads=[('request',{'task':'ctx-secret-marker','calling_system':'helper','run_id':'cli-run','privacy':'private'},3),('request',{'task':'write','calling_system':'helper','run_id':'cli-run','human_approved_tools':['write']},2),('request',{'task':'ctx-secret-marker','calling_system':'helper','run_id':'cli-run','verifier':True},2),('request',{'task':'x'},2),('decision',{'calling_system':'helper','run_id':'cli-run','state':{'secret':'state-marker'},'questions':{'fuzzy':{'kind':'noul','instructions':'prompt-marker'}}},3),('decision',{'calling_system':'helper','run_id':'cli-run','state':{},'questions':{'q':{'kind':'generate','instructions':'x'}}},2),('decision',{'calling_system':'helper','run_id':'cli-run','state':{},'questions':{},'deterministic_checks':{'success':True}},2),('providers',None,0)]
 for command,payload,code in payloads:
  child=subprocess.run([sys.executable,'-m','py_dev','ai',command],cwd='/Users/key/_AI-OS',env=env,input=json.dumps(payload) if payload is not None else '',text=True,capture_output=True)
  assert child.returncode==code and 'Traceback' not in child.stderr,(command,payload,child.returncode,child.stderr)
  parsed=json.loads(child.stdout) if child.stdout else None
  if command=='providers': assert all(not r['available'] and not r['tested'] and r['authenticated'] is None for r in parsed.values())
  if command=='decision' and code==3: assert (parsed['status'],parsed['branch'])==('UNAVAILABLE','REVIEW')
  results.append({'case':'public_cli','command':command,'exit':child.returncode,'status':parsed.get('status') if isinstance(parsed,dict) else None})
 events=(root/'events.jsonl').read_text(); assert not any(secret in events for secret in ['ctx-secret-marker','state-marker','prompt-marker'])
print(json.dumps(results,indent=2))
