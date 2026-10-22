from copy import deepcopy
import json
import pytest
from jsonschema import ValidationError
from lab.curriculum import CONCEPTS,CURRICULUM,POLICY
from lab.problems import PROBLEMS,PROBLEM_MAP,REPRESENTATIVE_IDS,validate_problem,learner_problem
from lab.store import StateError
from .conftest import prepared


def test_curriculum_and_exact_representative_budget():
    assert len(CURRICULUM['domains'])==18
    assert len(CONCEPTS)>=180 and len(CONCEPTS)==len(set(CONCEPTS))
    originals=[p for p in PROBLEMS if p['problem_id'] in REPRESENTATIVE_IDS]
    assert {p['kind']:sum(x['kind']==p['kind'] for x in originals) for p in originals}=={'sql':3,'modeling':2,'debug':1,'architecture':1}
    assert len([p for p in PROBLEMS if p['kind'] in ('sql','debug') and p['problem_id'] not in REPRESENTATIVE_IDS])==116
    assert len([p for p in PROBLEMS if p['kind']=='reasoning'])==60
    for p in PROBLEMS:validate_problem(p)
    assert list(POLICY['difficulty']['levels'])==['L1','L2','L3','L4','L5','L6']
    assert set(POLICY['modes'])=={'LEARN','PRACTICE','INTERVIEW','DEBUG','SYSTEM_DESIGN','INCIDENT','REVIEW','PERFORMANCE'}


def test_contract_rejects_private_extra_fields_and_unknown_tags():
    p=deepcopy(PROBLEMS[0]);p['answer_key']='secret'
    with pytest.raises(ValidationError):validate_problem(p)
    p=deepcopy(PROBLEMS[0]);p['mastery_tags']=['sql.unknown']
    with pytest.raises(ValueError):validate_problem(p)
    p=deepcopy(PROBLEMS[0]);p['learner_answer']={'sql':'the answer'}
    with pytest.raises(ValueError):validate_problem(p)
    p=deepcopy(PROBLEMS[0]);p['difficulty']['dimensions']['word_count']=1
    with pytest.raises(ValueError):validate_problem(p)


@pytest.mark.parametrize('p',PROBLEMS,ids=lambda p:p['problem_id'])
def test_positive_disclosure_allowlist(p):
    for mode in p['modes']:
        v=learner_problem(p,mode);body=json.dumps(v)
        assert not set(v)&{'solution','hints','hidden_tests','hidden_edge_cases','evaluation_rules','mastery_tags','transfer_from','recall'}
        assert p['solution'] not in body
        if POLICY['modes'][mode]['hide_skills']:
            assert 'skills_tested' not in v and 'scd2' not in body and 'sql.joins.fanout' not in body
        if mode=='INCIDENT':assert 'broken_sql' not in v['artifacts']


def test_requirements_first_hints_and_reveal_rules(engine):
    r=engine.start('SQL-LOAN-001')
    with pytest.raises(StateError):engine.action(r,'submit',{'sql':'SELECT 1','reason':'test'})
    with pytest.raises(StateError):engine.action(r,'reveal',{'explicit_request':True})
    first=engine.action(r,'hint')
    assert len(first['hints'])==1 and PROBLEM_MAP[r['problem_id']]['solution'] not in json.dumps(engine.view(first))
    for _ in range(3):first=engine.action(first,'hint')
    with pytest.raises(StateError):engine.action(first,'hint')
    r=engine.start('SQL-LOAN-001','INTERVIEW')
    with pytest.raises(StateError):engine.action(r,'hint')
    r=engine.start('SQL-LOAN-001','PRACTICE')
    r=engine.action(engine.action(r,'hint'),'hint')
    with pytest.raises(StateError):engine.action(r,'hint')


def test_grain_declarations_can_be_revised(engine):
    r=prepared(engine,'SQL-LOAN-001');r=engine.action(r,'revise')
    assert r['learning_step']==1
    with pytest.raises(StateError):engine.action(r,'submit',{'sql':'SELECT 1','reason':'x'})


def test_catalog_hides_concepts_in_advanced_modes(engine):
    for mode in ('INTERVIEW','DEBUG','SYSTEM_DESIGN','INCIDENT'):
        body=json.dumps(engine.catalog(mode))
        assert 'skills_tested' not in body and 'sql.joins.fanout' not in body
    assert len(engine.catalog())==len(PROBLEMS)
