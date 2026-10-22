from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import math
import psycopg
from sqlglot import exp
from .contracts import fingerprint
from .datasets import DOMAINS, fixture
from .oracles import expected, latest
from .postgres import Postgres, SQLRejected, parse_submission, value
from . import integrations


def canonical(value,numeric=True):
    if isinstance(value,bool):return value
    if isinstance(value,(int,float,Decimal)) or (numeric and isinstance(value,str) and value.lstrip('-').replace('.','',1).isdigit()):
        return str(Decimal(str(value)).normalize())
    if isinstance(value,str) and 'T' in value:
        try:
            parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
            return (parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed).isoformat()
        except ValueError:pass
    return value


def rowset(records,columns,types=None):
    return Counter(tuple(canonical(row.get(k),types is None or types.get(k)=='numeric') for k in columns) for row in records)


def compare(actual,reference,challenge):
    shape=set(actual['columns'])==set(challenge.output)
    types=challenge.output_types or None
    wanted=rowset(reference,challenge.output,types); got=rowset(actual['rows'],challenge.output,types)
    ordered=not challenge.ordered or [tuple(canonical(r.get(k),types is None or types.get(k)=='numeric') for k in challenge.output) for r in actual['rows']]==[tuple(canonical(r.get(k),types is None or types.get(k)=='numeric') for k in challenge.output) for r in reference]
    matches=shape and wanted==got and ordered
    return {'matches':matches,'columns_match':shape,'order_match':ordered,
            'missing_rows':[dict(zip(challenge.output,row)) for row,n in (wanted-got).items() for _ in range(n)],
            'unexpected_rows':[dict(zip(challenge.output,row)) for row,n in (got-wanted).items() for _ in range(n)]}


def risks(query,challenge):
    try:tree=parse_submission(query,challenge.inputs)
    except SQLRejected:return []
    flags=[]
    for window in tree.find_all(exp.Window):
        if isinstance(window.this,exp.RowNumber):
            order=window.args.get('order')
            flags.append({'code':'verify_total_order','classification':'potential_risk',
                'clause':window.sql(dialect='postgres'),
                'explanation':'Confirm that the window order uniquely identifies the required survivor. Equal business timestamps need an explicit tie policy; fixture success alone cannot prove determinism.'})
    for agg in tree.find_all(exp.Sum):
        if isinstance(agg.this,exp.Distinct):flags.append({'code':'sum_distinct','classification':'potential_risk','clause':agg.sql(dialect='postgres'),
            'explanation':'DISTINCT removes equal amounts, not duplicate transaction identities. Different transactions can have the same value.'})
    for select in tree.find_all(exp.Select):
        joins=list(select.find_all(exp.Join));where=select.args.get('where')
        if where:
            for join in joins:
                if join.side=='LEFT' and isinstance(join.this,exp.Table):
                    alias=join.this.alias_or_name
                    if any(col.table==alias for col in where.find_all(exp.Column)):
                        flags.append({'code':'left_where','classification':'potential_risk','clause':where.sql(dialect='postgres'),
                            'explanation':'A WHERE predicate on the nullable side can remove unmatched left rows. Check whether it deliberately tests IS NULL.'})
    if 'deduplication' in challenge.concepts and not any(tree.find_all(exp.Window)) and not any(tree.find_all(exp.Distinct)) and not any(tree.find_all(exp.Subquery)):
        flags.append({'code':'unresolved_event_grain','classification':'potential_risk','clause':next(tree.find_all(exp.Group),tree).sql(dialect='postgres'),
            'explanation':'This query has no visible version-selection step. Raw delivery grain can repeat logical transactions; inspect the measured cases.'})
    if 'scd2' in challenge.concepts:
        text=query.lower()
        if 'valid_to' not in text or 'valid_from' not in text:
            flags.append({'code':'scd_effective_join','classification':'potential_risk','clause':next(tree.find_all(exp.Join),tree).sql(dialect='postgres'),
                'explanation':'A business-key-only version join may match several effective versions. Use a start-inclusive, end-exclusive interval.'})
    return flags


def trace(challenge,data):
    if challenge.domain=='fintech':
        loans={r['loan_id']:r for r in data['loans']};chosen={r['transaction_id']:r for r in latest(data['payment_events'],'transaction_id')}
        traces=[]
        for identity,winner in chosen.items():
            events=[r for r in data['payment_events'] if r['transaction_id']==identity]
            traces.append({'transaction_id':identity,'event_ids':[r['event_id'] for r in events],
                'raw_sum_cents':sum(r['principal_cents'] or 0 for r in events),
                'selected_event_id':winner['event_id'],'selected_status':winner['status'],
                'eligible_principal_cents':(winner['principal_cents'] or 0) if winner['status']=='posted' and winner['currency']==loans[winner['loan_id']]['currency'] else 0})
        return {'classification':'independent_row_trace','note':'Raw sum versus logical transaction contribution. For cutoff exercises apply received_at before version selection.', 'rows':traces}
    return {'classification':'declared_lineage','rows':[],'note':'Compare the actual source rows, native join multiplicities, and output diff.'}


ERROR_CLASSES=('SYNTAX_ERROR','LOGIC_ERROR','GRAIN_ERROR','JOIN_ERROR','NULL_ERROR','WINDOW_ERROR',
               'DATE_ERROR','SEMANTIC_ERROR','EDGE_CASE_FAILURE','PERFORMANCE_CONCERN')

def classify(cases,declared):
    """Observable failure dimensions; this does not infer an unproven root cause."""
    classes=[]
    if not declared:classes.append('GRAIN_ERROR')
    errors=[c['error'] for c in cases if c.get('error')]
    if errors:classes.append('SYNTAX_ERROR' if any(e.get('sqlstate')=='42601' or e.get('cause_type')=='ParseError' for e in errors) else 'LOGIC_ERROR')
    failures=[c for c in cases if not c['matches'] and not c.get('error')]
    if failures:classes.append('EDGE_CASE_FAILURE' if cases[0]['matches'] else 'LOGIC_ERROR')
    return list(dict.fromkeys(classes))


def unexercised_techniques(query,challenge):
    """Equivalent SQL still passes; named technique evidence needs actual use."""
    techniques={'sql.windows.row_number':(exp.RowNumber,), 'sql.windows.rank_dense_rank':(exp.Rank,exp.DenseRank),
                'sql.windows.lag_lead':(exp.Lag,exp.Lead),'sql.windows.first_last':(exp.FirstValue,exp.LastValue),
                'sql.windows.ntile':(exp.Ntile,), 'sql.ctes.decomposition':(exp.CTE,)}
    try:tree=parse_submission(query,challenge.inputs)
    except SQLRejected:return list(techniques)
    return [tag for tag,kinds in techniques.items() if not any(isinstance(node,kinds) for node in tree.walk())]


def evaluate(challenge,query,grain,root,run_id,postgres=None):
    postgres=postgres or Postgres()
    cases=[]
    variants=(('clean',1),('adversarial',1),('adversarial',2),('recall',3))
    for variant,seed in variants:
        data=fixture(challenge.domain,variant,seed);reference=[{k:value(v) for k,v in row.items()} for row in expected(challenge.oracle,data)]
        case={'variant':variant,'seed':seed,'source_sha256':fingerprint(data),'expected':reference,
              'source_tables':{k:v for k,v in data.items() if k in challenge.inputs}}
        try:
            actual=postgres.execute(query,challenge,data)
            case.update(actual=actual,**compare(actual,reference,challenge),error=None)
        except (SQLRejected,psycopg.Error) as exc:
            case.update(actual={'columns':[],'rows':[]},matches=False,columns_match=False,error={'type':type(exc).__name__,'message':str(exc),
                'sqlstate':getattr(exc,'sqlstate',None),'cause_type':type(exc.__cause__).__name__,
                'position':getattr(getattr(exc,'diag',None),'statement_position',None)})
        cases.append(case)
    selected=next((c for c in cases if not c['matches']),cases[1])
    source=fixture(challenge.domain,selected['variant'],selected['seed'])
    native={}
    errors=[]
    infrastructure=next((c for c in cases if (c.get('error') or {}).get('type')=='OperationalError'),None)
    if infrastructure:errors.append({'system':'postgresql','message':infrastructure['error']['message']})
    if not selected['error']:
        for name,operation in (
            ('modeling',lambda:integrations.modeling(challenge,source,selected['actual'])),
            ('quality',lambda:integrations.quality(challenge,source,selected['actual'],run_id))):
            try:native[name]=operation()
            except Exception as e:errors.append({'system':name,'message':str(e)})
    try:native['observability']=integrations.observe(challenge,cases,root,run_id)
    except Exception as e:errors.append({'system':'observability','message':str(e)})
    keys=native.get('modeling',{}).get('keys',{}).get('candidate',[])
    key_ok=bool(keys) and all(k['status']=='pass' for k in keys)
    gate=native.get('quality',{}).get('bundles',{}).get('candidate',{}).get('gate',{}).get('status')
    input_ok=all(set(grain['inputs'].get(t,[]))==set(DOMAINS[challenge.domain].table(t).primary_key) for t in challenge.inputs)
    declared=input_ok and set(grain['output'])==set(challenge.output_key)
    passed=all(c['matches'] for c in cases) and key_ok and gate=='OPEN' and not errors and declared
    rate=sum(c['matches'] for c in cases)/len(cases)
    # SQL result equivalence and business columns are distinct rubric dimensions.
    business=0
    for case in cases:
        if case['error']:continue
        actual=case['actual']; cols=[k for k in challenge.output if k not in challenge.output_key]
        # Compare population and measured fields together: missing facts cost business accuracy.
        if set(challenge.output)<=set(actual['columns']):
            want=rowset(case['expected'],challenge.output,challenge.output_types or None);got=rowset(actual['rows'],challenge.output,challenge.output_types or None)
            business+=sum((want & got).values())/max(1,sum(want.values())) if want else int(not got)
    grade={'sql_correctness':round(40*rate,2),'modeling_grain':15 if declared and key_ok else 0,
           'business_accuracy':round(25*business/len(cases),2),'communication':None,'grain_reasoning':None,
           'available_automatic_points':80,'weights':{'sql_correctness':40,'modeling_grain':25,'business_accuracy':25,'communication':10},
           'manual_review':'10 points for grain reasoning and 10 for communication require tutor assessment; prose is never auto-certified.'}
    grade['automatic_total']=round(sum(v for k,v in grade.items() if k in ('sql_correctness','modeling_grain','business_accuracy')),2)
    issues=risks(query,challenge)
    if not declared:
        issues.insert(0,{'code':'grain_declaration','classification':'proven_violation','clause':None,
                        'explanation':'The declared keys do not represent the required input/output grains, even if output values match.'})
    if not passed:
        issues.insert(0,{'code':'execution_failure' if selected['error'] else 'fixture_mismatch','classification':'proven_violation',
            'clause':None,'explanation':selected['error']['message'] if selected['error'] else f"{selected['variant']} fixture: {len(selected['actual']['rows'])} actual rows versus {len(selected['expected'])} expected; exact key/value multiset differs."})
    feedback='All four fixture cases and native output constraints pass.' if passed else 'Inspect the first failing fixture and its row diff. Address one grain or value assumption, then resubmit.'
    if errors:feedback='Sibling validation unavailable; SQL evidence retained, acceptance withheld.'
    return {'status':'PASS' if passed else 'BLOCKED' if errors else 'FAIL','sql':query,'grade':grade,'cases':cases,
            'error_classes':[] if errors else classify(cases,declared),
            'unexercised_techniques':unexercised_techniques(query,challenge),
            'rubric':{'result_correctness':'PASS' if cases[0]['matches'] else 'FAIL',
                      'grain_correctness':'PASS' if declared and key_ok else 'FAIL',
                      'edge_case_robustness':'PASS' if all(c['matches'] for c in cases[1:]) else 'FAIL',
                      'business_interpretation':'REVIEW_REQUIRED','query_clarity':'REVIEW_REQUIRED','performance_awareness':'REVIEW_REQUIRED'},
            'grain_declared_correctly':declared,
            'selected_case':cases.index(selected),'issues':issues,'feedback':feedback,'followup':challenge.followup,
            'native':native,'integration_errors':errors,'row_trace':trace(challenge,source),
            'grain_declaration':grain,'provenance':'actual PostgreSQL output; independent Python oracle; sibling-owned key/quality/lineage evidence',
            'incorrect_assumptions':[i['code'] for i in issues],'execution_failures':sum(bool(c['error']) for c in cases),
            'logical_failures':sum(not c['matches'] and not c['error'] for c in cases)}
