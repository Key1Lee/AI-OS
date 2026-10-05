import sys, sqlite3, tempfile, json
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, '/Users/key/_AI-OS')
from py_dev import IntelligenceRequest, IntelligenceService, ModelRouter, ModelSettings, ToolDefinition
from py_dev.models import ProviderResult, ToolCall
from py_dev.providers import ProviderUnavailable
from py_dev.decisions import DecisionRequest, DecisionQuestion, DecisionService
from py_dev.budget import CloudCallBudget
EMPTY={'type':'object','properties':{},'required':[],'additionalProperties':False}
class SequenceProvider:
 def __init__(self,name,outcomes): self.name=name; self.model=name+'-test'; self.outcomes=list(outcomes); self.calls=[]
 def available(self): return True
 def generate(self,req):
  self.calls.append(req); outcome=self.outcomes.pop(0)
  if isinstance(outcome,Exception): raise outcome
  return outcome
def result(content='Completed1000',calls=(),model='openai-test'):
 return ProviderResult(content,model,'tool_call' if calls else 'completed',1,{'input_tokens':2},tuple(calls),())
def harness(outcomes,*,qwen=(),claude=()):
 providers={name:SequenceProvider(name, seq) for name,seq in [('openai',outcomes),('qwen_local',qwen),('claude',claude)]}
 events=[]; router=ModelRouter(ModelSettings(qwen_model='qwen_local-test',openai_model='openai-test',claude_model='claude-test',openai_enabled=True,claude_enabled=True,allow_cloud_escalation=True,cloud_call_budget=20),providers=providers,audit_sink=lambda e:None)
 return IntelligenceService(router=router,event_sink=events.append),providers,events
def request(**kwargs): return replace(IntelligenceRequest('Write expected records','independent-helper','run-1',provider='openai'),**kwargs)
checks=[]
with tempfile.TemporaryDirectory(prefix='aios-independent-') as tmp:
 con=sqlite3.connect(str(Path(tmp)/'state.db')); con.execute('create table rows (id integer primary key)'); con.executemany('insert into rows values (?)',[(i,) for i in range(700)]); con.commit()
 def count(): return con.execute('select count(*) from rows').fetchone()[0]
 service,providers,events=harness([result('Successfully wrote1000records')])
 out=service.run(request(verifier=lambda output,trace:count()==1000))
 assert count()==700 and out.status=='rejected' and out.verification_metadata['deterministic'] is False
 assert len(providers['openai'].calls)==1 and not providers['qwen_local'].calls and not providers['claude'].calls
 checks.append({'case':'false_success_sqlite','expected':1000,'actual':count(),'status':out.status,'verification':events[-1]['verification_status']})
 class MustNotDecide:
  calls=0
  def available(self): return True
  def evaluate(self,request): self.calls+=1; raise AssertionError('must not call')
 provider=MustNotDecide(); dec=DecisionService(provider,enabled=True,budget=CloudCallBudget(5),audit_sink=lambda e:None)
 verdict=dec.decide(DecisionRequest('independent-helper','run-failed',{'actual':count()},{'success':DecisionQuestion('noul','Was write successful?')}),deterministic_checks={'written_count':count()==1000},policy=lambda answers:'ALLOW')
 assert (verdict.status,verdict.branch,provider.calls)==('REJECTED','DENY',0)
 checks.append({'case':'probability_cannot_override_failure','status':verdict.status,'branch':verdict.branch,'provider_calls':provider.calls})
 reads=[]; writes=[]
 def read(args,key): value=count(); reads.append(value); return {'count':value}
 def write(args,key): con.executemany('insert into rows values (?)',[(i,) for i in range(700,1000)]); con.commit(); writes.append(key); return {'count':count()}
 readtool=ToolDefinition('read_count','Read actual rows',EMPTY,read)
 writetool=ToolDefinition('write','Insert300rows',EMPTY,write,mutating=True,verifier=lambda a,r:count()==1000)
 service,providers,events=harness([result(calls=(ToolCall('read-before','read_count',{}),ToolCall('write-1','write',{}),ToolCall('read-after','read_count',{}))),result('Observed stored state')])
 out=service.run(request(tools=(readtool,writetool),authorized_tools=frozenset({'read_count','write'}),human_approved_tools=frozenset({'write'}),verifier=lambda o,t:count()==1000))
 seen=[x.output for x in providers['openai'].calls[1].tool_outputs]
 assert reads == [700,1000] and seen == [{'count':700},{'count':1000},{'count':1000}]
 checks.append({'case':'read_write_read_reobservation','actual':count(),'handler_reads':reads,'native_tool_outputs':seen,'trace_status':[x['status'] for x in out.tool_trace],'status':out.status})
 # A successful mutation followed by lost provider response must remain uncertain.
 service,providers,events=harness([result(calls=(ToolCall('write1','touch',{}),)),ProviderUnavailable('lost after commit')],qwen=[result(model='qwen_local-test')],claude=[result(model='claude-test')])
 touched=[]; tool=ToolDefinition('touch','Commit marker',EMPTY,lambda a,k:touched.append(k),mutating=True,verifier=lambda a,r:len(touched)==1)
 out=service.run(request(tools=(tool,),authorized_tools=frozenset({'touch'}),human_approved_tools=frozenset({'touch'})))
 assert out.status=='uncertain' and len(touched)==1 and len(providers['openai'].calls)==2 and not providers['qwen_local'].calls and not providers['claude'].calls
 checks.append({'case':'mutation_failure_no_replay','status':out.status,'mutations':len(touched),'provider_calls':{k:len(v.calls) for k,v in providers.items()}})
 # Preflight must reject a complete batch before any mutation.
 touched=[]; service,providers,events=harness([result(calls=(ToolCall('write2','touch',{}),ToolCall('bad','unknown',{})))])
 out=service.run(request(tools=(tool,),authorized_tools=frozenset({'touch'}),human_approved_tools=frozenset({'touch'})))
 assert out.status=='rejected' and not touched
 checks.append({'case':'batch_authority_preflight','status':out.status,'mutations':len(touched)})
 # Private and pinned-model requests cannot relax requirements during fallback.
 for spec in [{'privacy':'private'},{'constraints':{'model':'different'}}]:
  service,providers,events=harness([result()],qwen=[result(model='qwen_local-test')],claude=[result(model='claude-test')])
  out=service.run(request(**spec)); assert not providers['openai'].calls and not providers['claude'].calls
  if 'constraints' in spec: assert not providers['qwen_local'].calls
  checks.append({'case':'privacy_or_model_pin','spec':spec,'status':out.status,'provider_calls':{k:len(v.calls) for k,v in providers.items()}})
 for bounds in [{'constraints':{'max_cloud_calls':1}},{'max_provider_calls':1}]:
  service,providers,events=harness([ProviderUnavailable('down')],qwen=[ProviderUnavailable('down')],claude=[result(model='claude-test')])
  out=service.run(request(**bounds)); assert out.status=='unavailable' and not providers['claude'].calls
  if 'max_provider_calls' in bounds: assert not providers['qwen_local'].calls
  checks.append({'case':'fallback_budget','bounds':bounds,'status':out.status,'calls':{k:len(v.calls) for k,v in providers.items()},'remaining_cloud':service.router.remaining_cloud_calls})
 con.close()
print(json.dumps(checks,indent=2))
