"""One reusable problem contract: preserved representatives and the SQL bank."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from importlib.resources import files
import json
from jsonschema import Draft202012Validator
from .curriculum import CONCEPTS, POLICY
from .sql_lab.catalog import CATALOG as SQL
from .sql_lab.datasets import DOMAINS, fixture
from .sql_lab.contracts import fingerprint
from .sql_lab.oracles import expected

SCHEMA=json.loads((files('contracts')/'problem.schema.json').read_text())
DIALECTS=json.loads((files('curriculum')/'sql-dialects.json').read_text())
VALIDATOR=Draft202012Validator(SCHEMA)
VERSION='ae-learning-v1'


def validate_problem(problem):
    VALIDATOR.validate(problem)
    if not set(problem['skills_tested']+problem['mastery_tags'])<=set(CONCEPTS):
        raise ValueError('Problem references unknown curriculum concepts')
    if not set(problem['difficulty']['dimensions'])<=set(POLICY['difficulty']['dimensions']):
        raise ValueError('Unknown difficulty dimension')
    if set(problem['sample_rows'])- {t['name'] for t in problem['tables']}:
        raise ValueError('Sample rows need a table contract')
    if problem['learner_answer'] is not None:
        raise ValueError('Authored problem cannot contain a learner answer')
    if problem['kind']=='reasoning':
        from .business_reasoning import validate_definition
        validate_definition(problem)
    return problem


def difficulty(level,reason,**dimensions):
    return {'level':level,'rationale':reason,'dimensions':dimensions}


def base(id,title,domain,kind,tags,level,context,inputs,requirements,output,solution,adapter,**extra):
    data=fixture(domain,'clean')
    problem={'contract_version':'ae-problem-v1','problem_id':id,'title':title,'neutral_title':title,'domain':domain,
      'business_context':context,'difficulty':level,'kind':kind,'skills_tested':list(tags),'mastery_tags':list(tags),
      'tables':[DOMAINS[domain].table(t).public() for t in inputs],
      'sample_rows':{t:data[t][:8] for t in inputs},'requirements':requirements,
      'expected_output_grain':output,'hidden_edge_cases':[],
      'learner_prompt':{'prediction':'Before running: what do you think could change the result?',
        'requirements':['What is the business question?','What does each input row represent?','What should an output row represent?',
                        'Which entities and joins matter?','Which edge cases matter? What does NULL mean?'],
        'proposal':'Describe your intended approach in one or two sentences before submitting.',
        'answer_fields':['inputs','output_key','requirements','proposal']},
      'learner_answer':None,'evaluation_rules':{'adapter':adapter,'criteria':['declared grain','independent business output','hidden edge cases']},
      'hidden_tests':[{'fixture':'adversarial','seed':1},{'fixture':'adversarial','seed':2},{'fixture':'recall','seed':3}],
      'followups':['How would a replay change this result? What evidence would you check?'],
      'hints':['Start at the layer that defines a row.','Compare the identity of a received record with the identity of the business entity.',
               'Inspect whether several source rows can contribute to the same business key.','Resolve each business identity at its required grain before aggregating.'],
      'solution':solution,'transfer_from':None,'modes':['LEARN','PRACTICE','INTERVIEW'],
      'artifacts':{'diagram':'flowchart TD\n source[Source records] --> model[Model]\n model --> quality[Quality]\n quality --> metric[Consumer output]',
                   'provenance':'Original company, dataset and scenario authored for AE Lab.'},
      'recall':[{'prompt':'What does grain describe?','accepted':['what one row represents','one row meaning','row meaning']}],
      **extra}
    return validate_problem(problem)

PROBLEMS=[]

for id,sql_id,title,tags,level,context,transfer in [
 ('SQL-LOAN-001','FIN-001','Harbor Lending: principal paid by loan',
  ['sql.deduplication.latest_version','sql.deduplication.deterministic_ties','sql.joins.left','modeling.grain.output_grain'],
  difficulty('L3','Versions, currency and missing activity matter beyond SQL syntax.',data_cleanliness=2,hidden_edge_cases=2,business_semantics=2),
  'Harbor Lending receives payment webhooks. Finance needs one principal-paid row for every loan, including loans with no activity.',None),
 ('SQL-ORDER-001','EC-001','Moss Market: net order value',
  ['sql.joins.fanout','modeling.grain.output_grain','sql.deduplication.latest_version'],
  difficulty('L3','Independent line and refund grains must be reconciled.',data_cleanliness=2,hidden_edge_cases=2,business_semantics=2),
  'Moss Market sells multiple products per order and delivers refund status webhooks. Finance needs lifetime net value per order.',None),
 ('SQL-INVOICE-001','SAAS-003','Orbit Desk: paid invoice population',
  ['sql.deduplication.latest_version','sql.deduplication.deterministic_ties','sql.deduplication.status_after_resolution'],
  difficulty('L2','A simpler output tests version-selection transfer in billing.',data_cleanliness=1,hidden_edge_cases=2,business_semantics=1),
  'Orbit Desk issues invoices with changing payment states. Revenue operations needs only invoices whose final payment status is paid.', 'SQL-LOAN-001')]:
    c=SQL[sql_id]
    problem=base(id,title,c.domain,'sql',tags,level,context,c.inputs,list(c.assumptions),c.output_grain,c.solution,'postgresql',transfer_from=transfer)
    problem['evaluation_rules'].update(sql_challenge_id=sql_id,required_columns=list(c.output))
    problem['requirements'].append('Return exactly these columns: '+', '.join(c.output)+'.')
    problem['learner_prompt']['answer_fields'].append('sql')
    problem['hidden_edge_cases']=['Repeated arrivals','Identical event timestamps','Reversal after payment','Changed amounts and row order','Missing activity']
    problem['recall']=[{'prompt':'Which identity groups event versions?','accepted':['transaction_id' if c.domain=='fintech' else 'refund_id' if c.domain=='ecommerce' else 'invoice_id']},
                       {'prompt':'What breaks equal latest timestamps deterministically?','accepted':['event_id','greatest event_id']},
                       {'prompt':'Should status be filtered before or after choosing the latest version?','accepted':['after','after latest selection']}]
    PROBLEMS.append(validate_problem(problem))

p=base('MODEL-GRAIN-001','Harbor Lending: source-to-model contract','fintech','modeling',
 ['modeling.grain.row_meaning','modeling.grain.natural_surrogate_keys','modeling.grain.output_grain'],
 difficulty('L2','Different event and transaction identities require explicit meaning.',requirement_ambiguity=1,business_semantics=2),
 'Harbor receives repeated payment deliveries. Declare the raw grain and the resolved transaction grain before any SQL exists.',
 ('payment_events',),['Declare input_grain and input_key for payment_events.','Declare output_grain and output_key for a resolved payment model.','Explain why transaction_id can repeat in raw arrivals.'],
 'one row per logical payment transaction',
 'Raw: received payment event keyed by event_id. Resolved: logical transaction keyed by transaction_id. A delivery surrogate is not a business transaction identity.',
 'native_modeling',modes=['LEARN','PRACTICE','INTERVIEW','SYSTEM_DESIGN'])
p['learner_prompt']['answer_fields']=['input_grain','input_key','output_grain','output_key','reason']
p['evaluation_rules']['expected']={'input_grain':['received payment event'],'input_key':[['event_id']],
                                  'output_grain':['logical payment transaction'],'output_key':[['transaction_id']]}
p['hidden_tests']=[{'input_grain':'received payment event','input_key':['event_id']},{'output_grain':'logical payment transaction','output_key':['transaction_id']}]
p['recall']=[{'prompt':'Can a delivery ID and business transaction ID mean the same grain?','accepted':['no','not necessarily']},
             {'prompt':'What does one resolved payment row represent?','accepted':['logical payment transaction','one transaction']}]
PROBLEMS.append(validate_problem(p))

p=base('MODEL-SCD-001','Orbit Desk: monthly contract history','saas','modeling',
 ['modeling.dimensions.scd2','modeling.dimensions.effective_intervals','modeling.design.additivity'],
 difficulty('L3','Business time, version keys and a reporting instant differ.',requirement_ambiguity=1,business_semantics=2,hidden_edge_cases=2),
 'Orbit Desk changes subscription rates at midnight. Specify the historical model and its as-of serving grain for a report exactly at that boundary.',
 ('subscription_versions','subscriptions'),
 ['Declare history input_grain and input_key, and as-of output_grain and output_key.',
  'Choose interval policy: closed or half_open. Choose snapshot aggregation: sum_across_dates or sum_entities_at_instant.',
  'The old version ends at October 3 and the new one starts then; NULL valid_to means infinity.'],
 'one subscription at one reporting instant',
 'History: one subscription version by version_id. Serving: one subscription at a reporting instant by subscription_id. Match valid_from <= as_of < valid_to (NULL infinity). Sum entities at one instant, not snapshots over dates.',
 'native_modeling',modes=['LEARN','PRACTICE','INTERVIEW','SYSTEM_DESIGN'])
p['learner_prompt']['answer_fields']=['input_grain','input_key','output_grain','output_key','interval','aggregation','reason']
p['evaluation_rules']['expected']={'input_grain':['subscription effective version'],'input_key':[['version_id']],
 'output_grain':['subscription at reporting instant'],'output_key':[['subscription_id']],'interval':['half_open'],'aggregation':['sum_entities_at_instant']}
p['hidden_tests']=[{'boundary':'2026-10-03T00:00:00+00:00','expected_versions':['V2','V3','V5']},{'valid_to':None,'meaning':'infinity'}]
p['hints']=['Start with the contract-history layer.','A business subscription can have several historical versions.',
 'At midnight, the old and new versions share a boundary. How many should match?',
 'Use a start-inclusive, end-exclusive interval. A snapshot balance is additive across entities at one instant.']
p['recall']=[{'prompt':'Does the end boundary belong to the old version?','accepted':['no']},
 {'prompt':'Can you sum MRR snapshots across successive dates?','accepted':['no']}]
PROBLEMS.append(validate_problem(p))

c=SQL['EC-001']
p=base('DEBUG-ORDER-001','Moss Market: a changed finance total','ecommerce','debug',
 ['sql.joins.fanout','modeling.grain.output_grain','debugging.data.fanout'],
 difficulty('L4','Observed wrong totals require causal diagnosis and a small repair.',incomplete_evidence=1,hidden_edge_cases=2,business_semantics=2),
 'Moss Market’s order report changed after a refund table was added. Investigate the provided query and repair the output.',
 c.inputs,list(c.assumptions),c.output_grain,c.solution,'postgresql',modes=['DEBUG','LEARN','PRACTICE','INTERVIEW','INCIDENT'])
p['neutral_title']='Moss Market: investigate the finance report'
p['evaluation_rules'].update(sql_challenge_id='EC-001',required_columns=list(c.output))
p['requirements'].append('Return exactly these columns: '+', '.join(c.output)+'.')
p['learner_prompt']['answer_fields'].append('sql')
p['artifacts']['broken_sql']="SELECT o.order_id,COALESCE(SUM(i.quantity*i.unit_cents),0)-COALESCE(SUM(r.refund_cents),0) AS net_cents FROM orders o LEFT JOIN order_items i USING(order_id) LEFT JOIN refund_events r USING(order_id) GROUP BY o.order_id"
p['artifacts']['symptom']='A finance total changed after the deployment; job execution is green. Publication is held pending row evidence.'
p['hints']=['Look at the model’s joins.','For one order, count line rows and refund rows separately.',
 'Trace how many joined rows each pair of source rows creates.',
 'Aggregate each many-side to order grain before joining; resolve refund versions before aggregating.']
p['recall']=[{'prompt':'Two lines join three refund rows. How many matched rows result?','accepted':[6,'6']},
 {'prompt':'At which grain should each many-side be aligned before the final join?','accepted':['order','order_id','one row per order']}]
PROBLEMS.append(validate_problem(p))

p=base('ARCH-PIPELINE-001','Harbor Lending: two consumers, different clocks','fintech','architecture',
 ['pipeline.ingestion.apis','pipeline.ingestion.cdc','pipeline.state.idempotency','observability.signals.freshness','system_design.architecture.consumers'],
 difficulty('L4','Consumer SLAs, recovery and system ownership dominate coding complexity.',requirement_ambiguity=2,systems_involved=3,reliability_constraints=2,scale=2,operational_risk=1),
 'Harbor has a daily payment API extract and committed loan changes in PostgreSQL. Collections wants balances within 15 minutes; finance wants reconciled daily totals by 07:00 UTC. Design the flow and ask for any missing requirement.',
 ('loans','payment_events'),['Declare Bronze/Silver/consumer grains.','Choose file/API/CDC methods from actual source constraints, and state replay/checkpoint identities.',
 'Separate consumer SLAs and schedules. Describe quality gates, table freshness, retries and a historical backfill.','Explain scale/cost tradeoffs and owner boundaries.'],
 'explicit layer grains and distinct consumer output grains',
 'Retain arrivals, extract the payment API by durable cursors and use CDC for committed loan changes; resolve logical versions in Silver. Serve distinct collections and finance models with separate SLAs. Gate finance on exact reconciliation and monitor table freshness separately from job success. Commit checkpoints after writes, replay idempotently and backfill affected historical partitions. Confirm whether the daily API can meet the 15-minute balance requirement; request a higher-frequency source or agree a different SLA.',
 'tutor_review',modes=['SYSTEM_DESIGN','LEARN','PRACTICE','INTERVIEW','INCIDENT'])
p['learner_prompt']['answer_fields']=['requirements','grains','proposal','design','recovery','tradeoffs']
p['evaluation_rules']['criteria']=['Identifies the daily-API/15-minute-SLA conflict before promising delivery.',
 'Declares event, transaction and consumer grains and time bases.','Names checkpoints and idempotent replay keys.',
 'Separates quality gates, monitoring and orchestration owners.','Explains backfill, cost, and acceptance evidence.']
p['hidden_tests']=[{'condition':'API only refreshes daily','question':'Can a 15-minute balance SLA be promised?'},
 {'condition':'partial write before cursor commit','question':'Is replay idempotent?'},
 {'condition':'late event in an old partition','question':'Which partition is repaired?'}]
p['hints']=['Start with the sources and each consumer’s deadline.','A successful scheduled job does not prove the consumer’s data is fresh.',
 'Can the daily payment extract meet the collections promise?',
 'State the incompatible source/SLA constraint. Use durable processing cursors, business keys, independent consumer models and explicit quality gates.']
p['recall']=[{'prompt':'Does a green job prove a table is fresh?','accepted':['no']},
 {'prompt':'When should a durable extraction checkpoint advance?','accepted':['after durable writes','after commit','after writes commit']}]
PROBLEMS.append(validate_problem(p))
# Each recall prompt certifies only its explicitly mapped concept.
for p in PROBLEMS:
    tags=p['mastery_tags']
    if p['kind']=='sql':
        targets=['sql.deduplication.latest_version','sql.deduplication.deterministic_ties','sql.deduplication.status_after_resolution']
        for q,tag in zip(p['recall'],targets):
            q['concepts']=[tag]
            if tag not in p['mastery_tags']:p['mastery_tags'].append(tag);p['skills_tested'].append(tag)
    elif p['problem_id']=='MODEL-GRAIN-001':
        p['recall'][0]['concepts']=['modeling.grain.natural_surrogate_keys']
        p['recall'][1]['concepts']=['modeling.grain.row_meaning']
    elif p['problem_id']=='MODEL-SCD-001':
        p['recall'][0]['concepts']=['modeling.dimensions.effective_intervals']
        p['recall'][1]['concepts']=['modeling.design.additivity']
    elif p['kind']=='debug':
        p['recall'][0]['concepts']=['sql.joins.fanout','debugging.data.fanout']
        p['recall'][1]['concepts']=['modeling.grain.output_grain']
    else:
        p['recall'][0]['concepts']=['observability.signals.freshness']
        p['recall'][1]['concepts']=['pipeline.state.idempotency']
    # Pin private fixture/oracle versions into the definition digest. Changing
    # a hidden test cannot silently reuse an earlier acceptance receipt.
    cases=[('clean',1),('adversarial',1),('adversarial',2),('recall',3)]
    p['hidden_tests'][0]['fixture_versions']={f'{v}:{s}':fingerprint(fixture(p['domain'],v,s)) for v,s in cases}
    sql_id=p['evaluation_rules'].get('sql_challenge_id')
    if sql_id:
        p['hidden_tests'][0]['oracle_versions']={f'{v}:{s}':fingerprint(expected(SQL[sql_id].oracle,fixture(p['domain'],v,s))) for v,s in cases}
    validate_problem(p)
REPRESENTATIVE_IDS=tuple(p['problem_id'] for p in PROBLEMS)
PROBLEMS.extend(validate_problem(p) for p in json.loads((files('curriculum')/'sql-bank.json').read_text()))
PROBLEMS.extend(validate_problem(p) for p in json.loads((files('curriculum')/'business-bank.json').read_text()))
PROBLEM_MAP={p['problem_id']:p for p in PROBLEMS}
if len(PROBLEM_MAP)!=len(PROBLEMS):raise ValueError('Problem IDs must be unique')


def learner_problem(problem,mode='LEARN'):
    """Positive allowlist: future private fields cannot leak by omission."""
    if mode not in problem['modes']:raise ValueError('This problem is unavailable in that mode')
    keys=('problem_id','domain','business_context','tables','sample_rows','requirements','expected_output_grain','learner_prompt')
    result={k:deepcopy(problem[k]) for k in keys}
    if problem['kind']=='reasoning':
        result.pop('expected_output_grain',None)
        result['tables']=[{'name':t['name'],'columns':deepcopy(t['columns'])} for t in problem['tables']]
    result['title']=problem['neutral_title'] if POLICY['modes'][mode]['hide_skills'] else problem['title']
    result['difficulty']={'level':problem['difficulty']['level']}
    if not POLICY['modes'][mode]['hide_skills']:
        # Keep incidental technique tags private until after the attempt. In
        # particular a metric-enrichment question must not announce fanout.
        result['skills_tested']=[t for t in problem['skills_tested'] if t!='sql.joins.fanout']
    else:
        result['tables']=[{k:v for k,v in t.items() if k in ('name','columns','primary_key','foreign_keys')}
                          for t in result['tables']]
    result['artifacts']={k:deepcopy(problem['artifacts'][k]) for k in ('diagram','symptom','dialect','response_type','join_pairs','window_reasoning','duplicate_reasoning','manual_criteria','scale_context') if k in problem['artifacts']}
    if mode in ('DEBUG','REVIEW') or problem['problem_id']=='DEBUG-ORDER-001':
        if 'broken_sql' in problem['artifacts']:result['artifacts']['broken_sql']=problem['artifacts']['broken_sql']
    if 'prediction_sql' in problem['artifacts']:result['artifacts']['prediction_sql']=problem['artifacts']['prediction_sql']
    if int(problem['difficulty']['level'][1])>=4 and problem['kind']!='reasoning':result['artifacts']['dialect_reference']=deepcopy(DIALECTS)
    if mode=='INCIDENT':
        result['artifacts'].pop('broken_sql',None)
        result['business_context']=problem['artifacts'].get('symptom','A consumer deadline is missed. Inspect the source constraints and evidence before proposing a cause.')
    return result
