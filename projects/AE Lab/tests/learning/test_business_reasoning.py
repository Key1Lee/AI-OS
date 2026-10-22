"""Step 3 business semantics and evidence boundaries; no live learner writes."""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import runpy
from pathlib import Path
import pytest
from lab.business_reasoning import evaluate,review_judgment,same,workbook,CATEGORIES,join_trace
from lab.curriculum import CONCEPTS
from lab.learning_engine import LearningEngine
from lab.problems import PROBLEMS,PROBLEM_MAP,validate_problem
from lab.reasoning_fixtures import facts,fixture,VARIANTS
from lab.sql_lab.contracts import fingerprint
from lab.sql_lab.datasets import fixture as sql_fixture
from lab.store import StateError,Store
_acceptance=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/validate_business_bank.py'))
BANK,prepare,reference_answer=(_acceptance[k] for k in ('BANK','prepare','reference_answer'))


def attempt(engine,pid='REASON-TRANSLATE-001',mode='LEARN',variant='sample'):
 r=engine.start(pid,mode);r['fixture_variant']=variant;engine.save(r)
 return engine.action(prepare(engine,r),'submit',reference_answer(PROBLEM_MAP[pid],variant))

def judgment(p,a,score=2):
 return {c:{'score':score,'evidence':a['answer']['decision'],
  'rationale':'Test tutor inspected the saved answer and its explicit source, population and uncertainty contract.'} for c in p['evaluation_rules']['criteria']}

def reviewed(engine,r,score=2):
 p=PROBLEM_MAP[r['problem_id']];a=r['attempts'][-1];j=judgment(p,a,score)
 return engine.review(r['run_id'],a['attempt_id'],'test tutor','Evidence-backed assessment of the saved response.',
  {k:score>=2 for k in j},p['mastery_tags'],judgment=j)


def test_budget_contexts_paths_and_realizable_mastery():
 assert len(BANK)==60 and len({p['problem_id'] for p in BANK})==60
 assert len({p['business_context'] for p in BANK})==60
 assert Counter(p['artifacts']['area'] for p in BANK)==dict.fromkeys(('translate','grain','entities','metrics','fanout','temporal','integrity','dimensions','validation','communication'),6)
 assert {p['domain'] for p in BANK}=={'iot','commerce','saas','payments','logistics','marketing','workforce','ai'}
 assert {p['difficulty']['level'] for p in BANK}=={'L1','L2','L3','L4','L5','L6'}
 graph={p['mastery_tags'][0]:p['evaluation_rules']['prerequisites'] for p in BANK}
 def visit(tag,seen):
  assert tag not in seen
  for parent in graph[tag]:visit(parent,seen|{tag})
 for tag in graph:visit(tag,set())
 tags={t for p in BANK for t in p['mastery_tags']}
 assert tags<=set(CONCEPTS) and len(tags)==40
 for tag in tags:
  available=[p for p in BANK if tag in p['mastery_tags']]
  assert len(available)>=3 and len({p['domain'] for p in available})>=2
  assert any(p['artifacts']['diagnosis_task'] for p in available)
  assert any(tag in q['concepts'] for p in available for q in p['recall'])
 for p in BANK:
  peer=PROBLEM_MAP[p['transfer_from']]
  assert peer['domain']!=p['domain'] and set(peer['mastery_tags'])&set(p['mastery_tags'])


@pytest.mark.parametrize('p',BANK,ids=lambda p:p['problem_id'])
def test_all_visible_variants_and_labeled_policies(p):
 validate_problem(p)
 for variant in VARIANTS:
  for policy in p['evaluation_rules']['policies']:
   a=reference_answer(p,variant,policy);e=evaluate(p,a,variant)
   assert e['status']=='REVIEW_REQUIRED' and e['objective_status']=='PASS'
   for check in p['evaluation_rules']['checks']:
    wrong=deepcopy(a);wrong['facts'][check['field']]=True
    assert evaluate(p,wrong,variant)['status']=='FAIL'
 assert 'calculation' not in json.dumps(workbook(p))
 assert 'expected' not in json.dumps(workbook(p))


def test_independent_hand_calculated_business_sentinels():
 x=facts('iot',fixture('iot'))
 assert (x['known_up_minutes'],x['known_minutes'],x['uptime_known'],x['joined_rows'])==('120','180','0.67',6)
 x=facts('iot',fixture('iot','edge'))
 assert (x['uptime_strict'],x['unknown_minutes'],x['coverage'],x['logical_events'],x['arrivals'])==(None,'60','0.75',4,5)
 assert (x['pre_close_events'],x['known_at_close'])==(3,2)
 x=facts('commerce',fixture('commerce'))
 assert (x['gross'],x['refunds'],x['net'],x['aov'],x['multiplied_gross'],x['distinct_amount_total'])==('10000','1000','9000','5000.00','15000','5000')
 x=facts('saas',fixture('saas'))
 assert (x['nrr'],x['grr'],x['opening'],x['new_revenue'])==('0.68','0.58','20000','5000')
 assert facts('saas',fixture('saas','edge'))['nrr'] is None
 x=facts('ai',fixture('ai'))
 assert (x['eligible_tasks'],x['success_final'],x['success_any'],x['cost'],x['multiplied_success'])==(3,'0.33','0.67','40',3)
 x=facts('workforce',fixture('workforce'))
 assert (x['headcount'],x['active_assignments'],x['fte'],x['hours'],x['multiplied_hours'])==(2,3,'2.0','18','28')
 x=facts('marketing',fixture('marketing'))
 assert (x['qualified'],x['qualified_credit_rows'],x['allocated'],x['invalid_weights'])==(1,2,'1.0',0)
 assert facts('marketing',fixture('marketing','edge'))['invalid_weights']==1
 x=facts('payments',fixture('payments'))
 assert (x['attempts'],x['payments'],x['capture_total'],x['attempt_amount'],x['no_capture'])==(3,3,'2000','4000',1)
 x=facts('logistics',fixture('logistics'))
 assert (x['delivered'],x['on_time_delivered'],x['on_time_all'],x['missing_delivery'])==(1,'1.00','0.33',2)
 assert facts('logistics',fixture('logistics','edge'))['orphan_events']==1


def test_sample_truth_is_not_physically_order_dependent_or_mutating_sql_sources():
 for d in ('iot','commerce','saas','payments','logistics','marketing','workforce','ai'):
  source=fixture(d,'edge');shuffled={k:list(reversed(v)) for k,v in source.items()}
  assert facts(d,source)==facts(d,shuffled)
 a=sql_fixture('commerce');before=fingerprint(a);business=fixture('commerce');business['orders'].clear()
 assert fingerprint(sql_fixture('commerce'))==before


def test_unseen_edge_data_never_rejects_a_visible_sample_answer(engine):
 r=attempt(engine);p=PROBLEM_MAP[r['problem_id']]
 assert r['attempts'][-1]['evaluation']['objective_status']=='PASS'
 assert r['attempts'][-1]['evaluation']['rubric']['edge_evidence']=='NOT_YET_OBSERVED'
 assert engine.mastery.state(p['mastery_tags'][0])['mastery_state']=='INTRODUCED'
 r=engine.action(r,'probe');assert r['fixture_variant']=='edge' and r['learning_step']==0
 with pytest.raises(StateError):engine.action(r,'probe')
 with pytest.raises(StateError):engine.action(r,'finish',{'connection':'Claim based on an earlier sample.'})
 r=prepare(engine,r);r=engine.action(r,'submit',reference_answer(p,'sample'))
 assert r['attempts'][-1]['status']=='FAIL'
 v=engine.view(r);assert v['reasoning_evidence']['variant']=='edge'
 assert v['reasoning_evidence']['checks'][0]['passed'] is False
 r=engine.action(r,'submit',reference_answer(p,'edge'))
 assert r['attempts'][-1]['assisted'] is True
 r=reviewed(engine,r);assert engine.mastery.state(p['mastery_tags'][0])['mastery_state']=='INTRODUCED'


def test_numeric_success_never_certifies_gibberish_judgment(engine):
 p=PROBLEM_MAP['REASON-METRICS-003'];r=prepare(engine,engine.start(p['problem_id']))
 a=reference_answer(p);a['decision']='banana';a['metric_contract']={f:'banana' for f in p['evaluation_rules']['metric_fields']}
 r=engine.action(r,'submit',a)
 assert r['state']=='REVIEW_PENDING' and not engine.mastery.state(p['mastery_tags'][0])['correct_attempts']
 r=reviewed(engine,r,score=0)
 assert r['state']=='RETRY' and engine.mastery.state(p['mastery_tags'][0])['failed_attempts']==1


def test_semantic_reviews_require_full_scores_real_quotes_and_no_objective_failure(engine):
 r=attempt(engine);p=PROBLEM_MAP[r['problem_id']];a=r['attempts'][-1];j=judgment(p,a)
 for changed in ('missing','fabricated','boolean'):
  bad=deepcopy(j);key=next(iter(bad))
  if changed=='missing':bad.pop(key)
  elif changed=='fabricated':bad[key]['evidence']='A fabricated answer that was never saved.'
  else:bad[key]['score']=True
  with pytest.raises(StateError):review_judgment(p,a,bad)
 with pytest.raises(StateError):engine.review(r['run_id'],a['attempt_id'],'tutor','rationale',{k:False for k in j},p['mastery_tags'],judgment=j)
 r=reviewed(engine,r)
 assert r['state']=='VERIFIED'
 assert engine.mastery.state(p['mastery_tags'][0])['mastery_state']=='APPLIED'
 with pytest.raises(StateError):reviewed(engine,r)
 failed=deepcopy(a);failed['evaluation']['objective_status']='FAIL'
 with pytest.raises(StateError):review_judgment(p,failed,j)


def test_reviewing_previous_evidence_cannot_complete_new_variant(engine):
 r=attempt(engine);p=PROBLEM_MAP[r['problem_id']];a=r['attempts'][-1]
 r=engine.action(r,'probe');j=judgment(p,a)
 r=engine.review(r['run_id'],a['attempt_id'],'tutor','Review of the actual earlier snapshot.',{k:True for k in j},p['mastery_tags'],judgment=j)
 assert r['fixture_variant']=='edge' and r['state']=='READY' and r['learning_step']==0


def test_clarification_has_no_disclosure_until_real_question_is_assessed(engine):
 r=engine.start('REASON-TRANSLATE-001');v=engine.view(r);body=json.dumps(v)
 assert not v['clarifications'] and 'essential' not in body and 'candidate_reasoning' not in body
 assert 'expected_output_grain' not in v['problem']
 for t in v['problem']['tables']:assert set(t)=={'name','columns'}
 r=engine.action(r,'predict',{'prediction':'What decision will the board make using this number?'})
 assert len(r['clarifications'])==1 and r['clarifications'][0]['status']=='PENDING_TUTOR_REVIEW'
 first=r['clarifications'][0]
 r=engine.respond_to_question(r['run_id'],first['question_id'],'tutor','essential','It identifies the decision the measure must support.',fact_id='decision')
 assert r['clarifications'][0]['category']=='essential' and not r['hints']
 with pytest.raises(StateError):engine.respond_to_question(r['run_id'],first['question_id'],'tutor','essential','Cannot reassess.',fact_id='decision')
 for category,fid in [('documented_assumption','rounding'),('minor','display'),('overengineering','platform'),('dangerous_assumption','unsafe')]:
  r=engine.action(r,'ask',{'question':'A test learner question for '+fid})
  q=r['clarifications'][-1]
  with pytest.raises(StateError):engine.respond_to_question(r['run_id'],q['question_id'],'tutor','essential','Mismatching category.',fact_id=fid)
  r=engine.respond_to_question(r['run_id'],q['question_id'],'tutor',category,'Semantic classification of this exact question.',fact_id=fid)
 assert {q['category'] for q in r['clarifications']}==set(CATEGORIES)
 assert not engine.mastery.state(PROBLEM_MAP[r['problem_id']]['mastery_tags'][0])['correct_attempts']


@pytest.mark.parametrize('mode',['LEARN','PRACTICE','INTERVIEW'])
def test_modes_finish_review_and_disclosure(engine,mode):
 r=attempt(engine,mode=mode);p=PROBLEM_MAP[r['problem_id']];v=engine.view(r)
 if mode=='INTERVIEW':
  assert not v['hint_limit'] and 'reasoning_evidence' not in v and 'rubric' not in v
  r=engine.action(r,'finish',{'connection':'The report requires an explicit population and observation contract.'})
  r=reviewed(engine,r);assert r['state']=='COMPLETED' and r['learning_step']==9
 else:
  with pytest.raises(StateError):engine.action(r,'finish',{'connection':'Cannot certify pending judgment.'})
  r=reviewed(engine,r);r=engine.action(r,'finish',{'connection':'Name the entity before selecting an additive measure.'})
 assert r['state']=='COMPLETED'
 assert engine.view(r)['reasoning_evidence']['variant']=='sample'


def test_numeric_and_identity_adversaries():
 assert same('0.670','0.67','number') and same(None,None,'number')
 for bad in (True,'NaN','Infinity','0.671',{},[]):assert not same(bad,'0.67','number')
 assert not same('null',None,'number')
 assert not same(['order_id','order_id'],['order_id'],'keys')
 assert not same(['order_id',' ORDER_ID '],['order_id'],'keys')
 assert not same('order_id',['order_id'],'keys')
 assert same(['ORDER_ID'],['order_id'],'keys')


def test_required_assumptions_policy_contract_and_diagnosis_are_enforced():
 p=PROBLEM_MAP['REASON-FANOUT-001'];answer=reference_answer(p)
 for key,value in [('assumptions',[]),('assumptions',[{'claim':'unknown','status':'certain','impact':'unknown'}]),('metric_contract',{}),('diagnosis',''),('repair',''),('policy','unapproved')]:
  a=deepcopy(answer);a[key]=value
  with pytest.raises(StateError):evaluate(p,a)
 p=deepcopy(p);p['hidden_tests'][0]['fixture_sha256']='invalid'
 with pytest.raises(ValueError):validate_problem(p)


def test_visual_trace_and_two_many_sides():
 p=PROBLEM_MAP['REASON-FANOUT-003'];trace=join_trace(p,fixture(p['domain']))
 assert [r['joined_rows'] for r in trace['rows']]==[4,1,1]
 assert sum(r['joined_rows'] for r in trace['rows'])==6
 p=PROBLEM_MAP['REASON-FANOUT-001'];trace=join_trace(p,fixture(p['domain']))
 assert sum(r['header_cents']*r['joined_rows'] for r in trace['rows'])==15000


def test_routing_prerequisites_weakness_and_repeated_task_credit(engine):
 first=engine.recommend(focus='reasoning');assert first['problem_id']=='REASON-TRANSLATE-001' and first['target_level']=='L3'
 p=PROBLEM_MAP[first['problem_id']]
 r=attempt(engine);r=reviewed(engine,r,0)
 recommendation=engine.recommend(focus='reasoning');q=PROBLEM_MAP[recommendation['problem_id']]
 assert q['domain']!=p['domain'] and q['artifacts']['area']=='translate'
 r=attempt(engine);r=reviewed(engine,r)
 tag=p['mastery_tags'][0]
 assert not engine.mastery.state(tag)['transfer_demonstrated']
 assert engine.mastery.state(tag)['mastery_state']!='MASTERED'


def test_business_mastery_can_reach_original_states_with_real_reviews_and_spaced_recall(tmp_path):
 now=datetime(2026,10,1,tzinfo=timezone.utc);engine=LearningEngine(Store(tmp_path/'proof'),clock=lambda:now)
 tag='business.translate.core'
 r=reviewed(engine,attempt(engine));assert engine.mastery.state(tag)['mastery_state']=='APPLIED'
 now+=timedelta(days=1);r=reviewed(engine,attempt(engine,'REASON-TRANSLATE-002'))
 assert engine.mastery.state(tag)['mastery_state']=='TRANSFERRED'
 now+=timedelta(days=2)
 r=engine.start_recall('REASON-TRANSLATE-001',tag)
 r=engine.action(r,'submit_recall',{'responses':['no']})
 now+=timedelta(days=4);r=reviewed(engine,attempt(engine,'REASON-TRANSLATE-003'))
 now+=timedelta(days=3);r=engine.start_recall('REASON-TRANSLATE-001',tag)
 r=engine.action(r,'submit_recall',{'responses':['no']})
 assert engine.mastery.state(tag)['mastery_state']=='MASTERED'


def test_roundtrip_old_runs_untouched_and_variant_pinned(engine):
 old=engine.start('SQL-CTE-001');before=fingerprint(old)
 r=attempt(engine);loaded=LearningEngine(engine.store).view(engine.store.get(r['run_id']))
 assert loaded['status']=='REVIEW_REQUIRED' and loaded['fixture_variant']=='sample'
 assert fingerprint(engine.store.get(old['run_id']))==before
 r=engine.start('REASON-TRANSLATE-001');assert r['fixture_variant']=='edge'
 r=engine.start('REASON-TRANSLATE-001');assert r['fixture_variant']=='revisit'


def test_tutor_feedback_is_visible_after_review_and_future_evidence_is_assisted(engine):
 r=attempt(engine,mode='INTERVIEW')
 r=engine.action(r,'finish',{'connection':'Report the population and unresolved business assumptions.'})
 r=reviewed(engine,r,0)
 assert r['reasoning_feedback_exposed'] is True
 v=engine.view(r)
 assert v['rubric']['judgment']=='FAIL' and v['judgment_review']['passed'] is False
 assert 'Reasoning needs revision' in v['feedback']['error']
 r=engine.action(r,'probe');r=prepare(engine,r)
 r=engine.action(r,'submit',reference_answer(PROBLEM_MAP[r['problem_id']],'edge'))
 assert r['attempts'][-1]['assisted']


def test_cli_reasoning_catalog_and_trusted_response(tmp_path,capsys):
 from lab.learning_cli import main
 root=tmp_path/'cli';engine=LearningEngine(Store(root));r=engine.start('REASON-GRAIN-003')
 r=engine.action(r,'predict',{'prediction':'Which producer identity represents one logical heartbeat? A unique received row is not a guarantee.'})
 path=tmp_path/'response.json';path.write_text(json.dumps({'reviewer':'test tutor','category':'essential',
  'rationale':'The question distinguishes receipt identity from logical event identity.','fact_id':'identity'}))
 assert main(['--state-dir',str(root),'catalog','--focus','reasoning'])==0
 assert len(json.loads(capsys.readouterr().out))==60
 assert main(['--state-dir',str(root),'respond',r['run_id'],r['clarifications'][0]['question_id'],'--response-file',str(path)])==0
 response=json.loads(capsys.readouterr().out)['clarifications'][0]
 assert response['category']=='essential' and 'event_id' in response['response']
