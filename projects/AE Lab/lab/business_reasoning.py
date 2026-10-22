"""Stateless assessment helpers for LearningEngine's business cases.

No new learner store, SQL executor, metric governance or keyword prose grader.
"""
from copy import deepcopy
from decimal import Decimal,InvalidOperation
from .reasoning_fixtures import fixture,facts,groups,active,VARIANTS
from .sql_lab.contracts import fingerprint
from .store import StateError

CATEGORIES=('essential','documented_assumption','minor','overengineering','dangerous_assumption')
ASSUMPTION_STATES=('confirmed','documented','pending','blocker')


def short(value,label,limit=6000):
 if not isinstance(value,str) or not value.strip() or len(value)>limit:raise StateError(f'{label}: enter a nonempty response, at most {limit} characters')
 return value.strip()

def expected_for(p,variant,policy):
 data=fixture(p['domain'],variant);fv=facts(p['domain'],data)
 return {c['field']:fv[c.get('calculation') or c['calculation_by_policy'][policy]] for c in p['evaluation_rules']['checks']}

def validate_definition(p):
 rules=p['evaluation_rules'];checks=rules['checks'];policies=rules['policies']
 if not checks or len({c['field'] for c in checks})!=len(checks):raise ValueError('Reasoning objective fields must be distinct')
 if not policies or any(c['type'] not in ('number','keys','text') for c in checks):raise ValueError('Invalid reasoning objective contract')
 if {t['variant'] for t in p['hidden_tests']}!=set(VARIANTS):raise ValueError('All reasoning fixture variants are required')
 if p['artifacts']['diagnosis_task'] and not p['artifacts']['candidate_reasoning']:raise ValueError('Diagnosis task needs an actual candidate')
 if any(q['category'] not in CATEGORIES for q in rules['clarifications']):raise ValueError('Invalid clarification category')
 for test in p['hidden_tests']:
  data=fixture(p['domain'],test['variant'])
  if test['fixture_sha256']!=fingerprint(data):raise ValueError('Reasoning fixture definition changed; regenerate the bank')
  for policy in policies:
   if expected_for(p,test['variant'],policy)!=test['expected'][policy]:raise ValueError('Reasoning reference and fixture disagree')
 return p

def workbook(p):
 rules=p['evaluation_rules']
 return {'checks':[{k:c[k] for k in ('field','prompt','type')} for c in rules['checks']],
  'policies':deepcopy(rules['policies']),'metric_fields':list(rules['metric_fields']),
  'candidate_reasoning':p['artifacts']['candidate_reasoning'],'diagnosis_task':p['artifacts']['diagnosis_task'],
  'instructions':'Use the displayed extract and stated boundaries. If a contract field is not applicable, explain why. Label unresolved assumptions.'}

def join_trace(p,data):
 """Post-attempt visual multiplicity, derived from the actual displayed rows."""
 pid=p['problem_id'];rows=[]
 if pid in ('REASON-GRAIN-001','REASON-FANOUT-001'):
  children=groups(data['items'],'order_id')
  for parent in data['orders']:
   if pid=='REASON-FANOUT-001' and parent['status']!='fulfilled':continue
   matched=children[parent['order_id']]
   rows.append({'order':parent['order_id'],'item_ids':[r['item_id'] for r in matched],'joined_rows':max(1,len(matched)),'header_cents':parent['gross_cents']})
 elif pid=='REASON-FANOUT-003':
  intervals=groups(data['intervals'],'device_id');trips=groups(data['trips'],'device_id')
  for d in data['devices']:
   key=d['device_id'];rows.append({'device':key,'intervals':[r['interval_id'] for r in intervals[key]],'trips':[r['trip_id'] for r in trips[key]],'joined_rows':max(1,len(intervals[key]))*max(1,len(trips[key]))})
 elif pid in ('REASON-GRAIN-002','REASON-FANOUT-002'):
  child='touches' if pid=='REASON-GRAIN-002' else 'lead_credit';key='user_id' if child=='touches' else 'lead_id';matches=groups(data[child],key)
  for lead in data['leads']:
   matched=matches[lead[key]];rows.append({'lead':lead['lead_id'],'child_rows':len(matched),'left_join_rows':max(1,len(matched))})
 elif pid=='REASON-FANOUT-004':
  matches=groups(data['assignments'],'employment_id')
  for entry in data['time_entries']:
   matched=[a for a in matches[entry['employment_id']] if active(a,entry['day']+'T00:00:00+00:00','valid_from','valid_to')]
   rows.append({'entry':entry['entry_id'],'assignments':[a['assignment_id'] for a in matched],'source_hours':entry['hours'],'enriched_hours':entry['hours']*len(matched)})
 elif pid=='REASON-FANOUT-005':
  matches=groups(data['tool_calls'],'attempt_id')
  for a in data['attempts']:rows.append({'task':a['task_id'],'attempt':a['attempt_id'],'status':a['status'],'approved':a['approved'],'call_rows':len(matches[a['attempt_id']])})
 elif pid=='REASON-FANOUT-006':
  attempts=groups(data['attempts'],'payment_id');captures=groups(data['captures'],'payment_id')
  for key,aa in attempts.items():rows.append({'payment':key,'attempt_rows':len(aa),'capture_rows':len(captures[key]),'left_join_rows':len(aa)*max(1,len(captures[key]))})
 return {'note':'Match the listed child identities to each parent. Independent many sides create combinations; parent measures repeat in those rows.','rows':rows} if rows else None

def same(actual,wanted,kind):
 if kind=='keys':
  if not isinstance(actual,list) or not all(isinstance(k,str) for k in actual):return False
  normalized=[k.strip().casefold() for k in actual]
  return all(normalized) and len(set(normalized))==len(normalized) and set(normalized)=={k.casefold() for k in wanted}
 if kind=='number':
  if wanted is None:return actual is None
  if actual is None or isinstance(actual,bool) or not isinstance(actual,(int,float,str)):return False
  try:
   a=Decimal(str(actual));w=Decimal(str(wanted))
   return a.is_finite() and a==w
  except InvalidOperation:return False
 return isinstance(actual,str) and actual.strip().casefold()==str(wanted).casefold()

def evaluate(p,answer,variant='sample'):
 rules=p['evaluation_rules'];policy=answer.get('policy','specified')
 if not isinstance(policy,str) or policy not in rules['policies']:raise StateError('Choose an authorized labeled definition')
 submitted=answer.get('facts')
 if not isinstance(submitted,dict) or set(submitted)!={c['field'] for c in rules['checks']}:raise StateError('Answer each objective question with its declared field name')
 short(answer.get('decision'),'decision and stakeholder explanation')
 contract=answer.get('metric_contract')
 if not isinstance(contract,dict) or not set(rules['metric_fields'])<=set(contract):raise StateError('Complete each applicable metric-contract field')
 for name in rules['metric_fields']:short(contract[name],name,1600)
 assumptions=answer.get('assumptions')
 if not isinstance(assumptions,list) or not 1<=len(assumptions)<=12:raise StateError('Record at least one known, documented, pending or blocking assumption')
 for a in assumptions:
  if not isinstance(a,dict) or a.get('status') not in ASSUMPTION_STATES:raise StateError('Assumption status must be confirmed, documented, pending or blocker')
  short(a.get('claim'),'assumption claim',1600);short(a.get('impact'),'assumption impact',1600)
 if p['artifacts']['diagnosis_task']:
  short(answer.get('diagnosis'),'candidate diagnosis',3000);short(answer.get('repair'),'proposed correction',3000)
 test=next(t for t in p['hidden_tests'] if t['variant']==variant)
 if fingerprint(fixture(p['domain'],variant))!=test['fixture_sha256']:raise RuntimeError('Reasoning fixtures changed; regenerate and validate before acceptance')
 wanted=expected_for(p,variant,policy)
 checks=[{'field':c['field'],'prompt':c['prompt'],'actual':submitted[c['field']],'expected':wanted[c['field']],
          'passed':same(submitted[c['field']],wanted[c['field']],c['type'])} for c in rules['checks']]
 failure=next((c for c in checks if not c['passed']),None)
 feedback=None
 if failure:
  feedback={'error':failure['prompt']+' The submitted fact differs from the displayed evidence.',
   'fix':'The source result is '+json_value(failure['expected'])+'. '+rules['resolution'][:300],'why':rules['common_error'][:350],
   'try_again':p['followups'][0]}
 return {'status':'FAIL' if failure else 'REVIEW_REQUIRED','objective_status':'FAIL' if failure else 'PASS',
  'criteria':list(rules['criteria']),'checks':checks,'variant':variant,'policy':policy,
  'source_sha256':test['fixture_sha256'],'business_feedback':feedback,
  'error_classes':['SEMANTIC_ERROR'] if failure else [],
  'rubric':{'objective_facts':'FAIL' if failure else 'PASS','judgment':'REVIEW_REQUIRED',
            'edge_evidence':'OBSERVED' if variant!='sample' else 'NOT_YET_OBSERVED'},
  'scope':'Objective facts for the visible fixture only. Decision quality requires evidence-backed semantic tutor review.'}

def json_value(value):
 if value is None:return 'unknown (null), not a known zero'
 if isinstance(value,list):return ', '.join(value)
 return str(value)


def review_judgment(p,attempt,judgment):
 criteria=attempt['evaluation']['criteria']
 if attempt['evaluation'].get('objective_status')!='PASS':raise StateError('Correct objective facts before approving reasoning quality')
 if not isinstance(judgment,dict) or set(judgment)!=set(criteria):raise StateError('Score every authored semantic criterion with evidence and rationale')
 material=str(attempt['answer'])+str(attempt.get('context',{}))+str(attempt.get('question_snapshot',[]))
 result={}
 for criterion,row in judgment.items():
  if not isinstance(row,dict) or type(row.get('score')) is not int or row['score'] not in range(4):raise StateError('Semantic criterion scores must be integers 0–3')
  quote=short(row.get('evidence'),'learner evidence quote',1200)
  if quote not in material:raise StateError('Each semantic score needs an exact quote from this saved attempt or its preceding questions')
  short(row.get('rationale'),'semantic rationale',3000)
  result[criterion]=row['score']>=2
 return result
