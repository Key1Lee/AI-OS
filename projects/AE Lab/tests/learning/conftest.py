from datetime import datetime, timezone
import pytest
from lab.learning_engine import LearningEngine
from lab.store import Store
from lab.problems import PROBLEM_MAP
from lab.sql_lab.catalog import CATALOG
from lab.sql_lab.datasets import DOMAINS

@pytest.fixture
def engine(tmp_path):
    return LearningEngine(Store(tmp_path/'learning'),clock=lambda:datetime(2026,10,14,0,0,tzinfo=timezone.utc))

def prepared(engine,problem_id,mode='LEARN'):
    r=engine.start(problem_id,mode);p=PROBLEM_MAP[problem_id]
    r=engine.action(r,'predict',{'prediction':'A repeated business identity or changing row grain can change the output.'})
    a={'requirements':'Preserve the required population, exact cents and status meaning.','proposal':'Resolve identities before joining or aggregating.',
       'input_grain':'One received source event or producer business entity.','output_grain':p['expected_output_grain']}
    if p['kind'] in ('sql','debug'):
        c=CATALOG[p['evaluation_rules']['sql_challenge_id']]
        a.update(inputs={t:list(DOMAINS[c.domain].table(t).primary_key) for t in c.inputs},output_key=list(c.output_key))
        a['joins']={pair:{'left_grain':DOMAINS[c.domain].table(pair.split(':')[0]).grain,'right_grain':DOMAINS[c.domain].table(pair.split(':')[1]).grain,
                         'relationship':rel,'output_grain':c.output_grain} for pair,rel in engine.join_rules(p,r).items()}
    return engine.action(r,'prepare',a)

def solved(engine,problem_id,mode='LEARN'):
    r=prepared(engine,problem_id,mode);p=PROBLEM_MAP[problem_id]
    if p['kind'] in ('sql','debug'):a={'sql':p['solution'],'reason':'Logical identity is resolved and aggregation is aligned with consumer grain.'}
    elif p['kind']=='modeling':a={k:v[0] for k,v in p['evaluation_rules']['expected'].items()}|{'reason':'The declared key distinguishes versions from business entities.'}
    else:a={'design':p['solution'],'reason':'Source cadence must support the consumer SLA before selecting a serving design.'}
    return engine.action(r,'submit',a)
