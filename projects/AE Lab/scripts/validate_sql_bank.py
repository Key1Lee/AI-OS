"""Validate real SQL, independent oracles, hidden cases and native constraints.

Writes a receipt without solutions/hidden rows. It never touches learner state.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab.problems import PROBLEMS,REPRESENTATIVE_IDS,validate_problem,learner_problem
from lab.sql_lab.catalog import CATALOG
from lab.sql_lab.contracts import fingerprint
from lab.sql_lab.datasets import DOMAINS,fixture
from lab.sql_lab.evaluator import evaluate,compare
from lab.sql_lab.oracles import expected
from lab.sql_lab.postgres import Postgres,SQLRejected


def validate_one(p,root):
    validate_problem(p);c=CATALOG[p['evaluation_rules']['sql_challenge_id']];pg=Postgres()
    grain={'inputs':{t:list(DOMAINS[c.domain].table(t).primary_key) for t in c.inputs},'output':list(c.output_key)}
    folder=root/p['problem_id'];folder.mkdir(parents=True,exist_ok=True)
    result=evaluate(c,c.solution,grain,folder,'validate-'+p['problem_id'],pg)
    errors=[]
    if result['status']!='PASS':errors.append({'native_or_reference':result['integration_errors'] or result['issues']})
    for test,case in zip(p['hidden_tests'],result['cases']):
        if p['problem_id'].startswith(('SQL-FND','SQL-AGG','SQL-GRN','SQL-JOIN','SQL-CTE','SQL-WIN','SQL-DED','SQL-DATE','SQL-PAT','SQL-ADV','SQL-XFR')):
            if test['fixture_sha256']!=case['source_sha256'] or test['oracle_sha256']!=fingerprint(expected(c.oracle,fixture(c.domain,case['variant'],case['seed']))):errors.append('Private fixture/oracle digest mismatch')
    # An independently structured equivalent query must be accepted.
    alternate='WITH answer_candidate AS ('+c.solution+') SELECT * FROM answer_candidate'
    if c.ordered:alternate+=' ORDER BY gross_cents DESC,order_id ASC'
    data=fixture(c.domain,'adversarial',2)
    alternate_matches=compare(pg.execute(alternate,c,data),expected(c.oracle,data),c)['matches']
    if not alternate_matches:errors.append('Equivalent SQL rejected')
    broken=p['artifacts'].get('broken_sql');detected=None
    if broken:
        detected=False
        for v,seed in [('clean',1),('adversarial',1),('adversarial',2),('recall',3)]:
            data=fixture(c.domain,v,seed)
            try:detected|=not compare(pg.execute(broken,c,data),expected(c.oracle,data),c)['matches']
            except psycopg.OperationalError:raise
            except (SQLRejected,psycopg.Error):detected=True
        if not detected:errors.append('Authored broken query was not distinguished by fixtures')
    for mode in p['modes']:
        view=learner_problem(p,mode)
        if p['solution'] in json.dumps(view) or {'solution','hidden_tests','evaluation_rules','transfer_from'} & set(view):errors.append('Disclosure failure')
    return {'problem_id':p['problem_id'],'level':p['difficulty']['level'],'domain':p['domain'],
            'definition_sha256':fingerprint(p),'fixture_cases':len(result['cases']),'native_status':result['status'],
            'alternate_equivalent':alternate_matches,'broken_query_detected':detected,'errors':errors}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'docs/sql-engine-validation.json');args=parser.parse_args()
    Postgres().health()
    problems=[p for p in PROBLEMS if p['kind'] in ('sql','debug')]
    root=ROOT/'.lab/sql-engine-validation';root.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:receipts=list(pool.map(lambda p:validate_one(p,root),problems))
    failures=[r for r in receipts if r['errors']]
    report={'validated_at':datetime.now(timezone.utc).isoformat(),'status':'FAIL' if failures else 'PASS',
      'execution':Postgres().health(),'problem_count':len(receipts),'new_problem_count':sum(p['problem_id'] not in REPRESENTATIVE_IDS for p in problems),
      'levels':dict(sorted(Counter(r['level'] for r in receipts).items())),
      'domains':sorted({r['domain'] for r in receipts}),'fixture_cases':sum(r['fixture_cases'] for r in receipts),
      'receipts':receipts}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='receipts'},indent=2))
    for failure in failures:print(json.dumps(failure))
    return bool(failures)

if __name__=='__main__':sys.exit(main())
