from copy import deepcopy
from datetime import datetime, timedelta,timezone
import pytest
from lab.mastery import Mastery
from lab.curriculum import CONCEPTS
from lab.learning_engine import LearningEngine
from lab.problems import PROBLEM_MAP,PROBLEMS
from lab.store import Store,StateError
from .conftest import solved,prepared

TAG='sql.deduplication.latest_version'
T0=datetime(2026,10,14,tzinfo=timezone.utc)


def add(engine,kind,pid,days=0,passed=True,assisted=False,**kw):
    p=PROBLEM_MAP[pid]
    return engine.mastery.add(TAG,kind,p,(T0+timedelta(days=days)).isoformat(),passed=passed,assisted=assisted,
                             reference=kw.pop('reference',f'{pid}:{kind}:{days}'),**kw)


def test_one_correct_answer_repetition_and_assistance_do_not_master(engine):
    add(engine,'introduced','SQL-LOAN-001',passed=None)
    for day in range(10):add(engine,'applied','SQL-LOAN-001',days=day)
    s=engine.mastery.state(TAG)
    assert s['mastery_state']=='INTRODUCED' and not s['transfer_demonstrated']
    add(engine,'understood','SQL-LOAN-001',reviewer='Tutor',note='Explained business identity, delivery identity and deterministic selection.')
    assert engine.mastery.state(TAG)['mastery_state']=='APPLIED'
    for day in (3,8):add(engine,'recall','SQL-LOAN-001',days=day)
    assert engine.mastery.state(TAG)['mastery_state']=='APPLIED'
    add(engine,'applied','SQL-INVOICE-001',days=8,assisted=True)
    assert not engine.mastery.state(TAG)['transfer_demonstrated']


def test_missing_debugging_transfer_or_recall_prevents_mastery(engine):
    add(engine,'understood','SQL-LOAN-001',reviewer='Tutor',note='Reviewed causal reasoning.')
    add(engine,'applied','SQL-LOAN-001')
    add(engine,'applied','SQL-INVOICE-001',days=2)
    assert engine.mastery.state(TAG)['transfer_demonstrated']
    assert engine.mastery.state(TAG)['mastery_state']=='APPLIED'
    # Same-task diagnosis cannot replace a different debugging task.
    add(engine,'debugged','SQL-LOAN-001',days=0,reviewer='Tutor',note='Same task only.')
    # Later invoice application happened after this review, so it cannot establish
    # an earlier application before a distinct debugging task.
    assert engine.mastery.state(TAG)['mastery_state']=='APPLIED'
    debug=deepcopy(PROBLEM_MAP['DEBUG-ORDER-001']);debug['mastery_tags'].append(TAG)
    engine.mastery.add(TAG,'debugged',debug,(T0+timedelta(days=3)).isoformat(),passed=True,
       reviewer='Tutor',note='Diagnosed version-related duplication and repaired a different task.',reference='debug-real-task')
    assert engine.mastery.state(TAG)['mastery_state']=='TRANSFERRED'
    add(engine,'recall','SQL-LOAN-001',days=4)
    assert engine.mastery.state(TAG)['mastery_state']=='TRANSFERRED'
    add(engine,'recall','SQL-INVOICE-001',days=8)
    assert engine.mastery.state(TAG)['mastery_state']=='MASTERED'


def test_transfer_needs_different_task_domain_and_later_day(engine):
    add(engine,'applied','SQL-LOAN-001')
    add(engine,'applied','SQL-INVOICE-001',days=0)
    assert not engine.mastery.state(TAG)['transfer_demonstrated']
    add(engine,'applied','SQL-INVOICE-001',days=1)
    assert engine.mastery.state(TAG)['transfer_demonstrated']


def test_reviewed_evidence_and_identity_are_required(engine):
    with pytest.raises(ValueError):add(engine,'understood','SQL-LOAN-001')
    item=add(engine,'attempt','SQL-LOAN-001',identity='immutable')
    p=PROBLEM_MAP['SQL-LOAN-001']
    again=engine.mastery.add(TAG,'attempt',p,item['at'],passed=True,reference=item['reference'],identity='immutable')
    assert again==item
    with pytest.raises(ValueError):engine.mastery.add(TAG,'attempt',p,item['at'],passed=False,reference=item['reference'],identity='immutable')


def test_failed_concept_returns_in_different_simpler_context(engine):
    add(engine,'attempt','SQL-LOAN-001',passed=False)
    add(engine,'attempt','SQL-LOAN-001',passed=False)
    rec=engine.mastery.select(PROBLEMS,T0.isoformat())
    assert rec['kind']=='problem' and rec['problem_id']=='SQL-INVOICE-001'
    assert PROBLEM_MAP[rec['problem_id']]['domain']!='fintech' and rec['target_level']=='L2'
    assert PROBLEM_MAP[rec['problem_id']]['transfer_from']=='SQL-LOAN-001'


def test_no_different_context_reports_real_coverage_gap(engine):
    p=PROBLEM_MAP['MODEL-SCD-001'];tag=p['mastery_tags'][0]
    engine.mastery.add(tag,'attempt',p,T0.isoformat(),passed=False,reference='scd-failure')
    rec=engine.mastery.select(PROBLEMS,T0.isoformat())
    assert rec['kind']=='gap' and tag in rec['concepts']


def test_selection_prefers_unseen_over_strong_repeated_problem(engine):
    add(engine,'attempt','SQL-INVOICE-001')
    rec=engine.mastery.select(PROBLEMS,T0.isoformat())
    assert rec['kind']=='problem' and rec['problem_id']!='SQL-INVOICE-001'


def test_spaced_recall_due_persistence_and_native_short_checks(engine):
    r=solved(engine,'SQL-INVOICE-001');p=PROBLEM_MAP[r['problem_id']];tag=p['mastery_tags'][0]
    with pytest.raises(StateError):engine.start_recall(p['problem_id'],tag)
    later=LearningEngine(Store(engine.store.root),clock=lambda:T0+timedelta(days=1))
    rec=later.mastery.select(PROBLEMS,later.now());assert rec['kind']=='recall'
    recall=later.start_recall(p['problem_id'],tag)
    view=later.view(recall);assert len(view['prompts'])<=3 and 'accepted' not in str(view)
    response=[q['accepted'][0] for q in recall['recall_questions']]
    recall=later.action(recall,'submit_recall',{'responses':response})
    assert recall['answers']['evaluation']['outcome']=='pass'
    assert recall['answers']['evaluation']['provenance']['system']=='Toptal-Testing System'
    assert later.mastery.state(tag)['due_recall']==(T0+timedelta(days=4)).isoformat()
    with pytest.raises(StateError):later.action(recall,'submit_recall',{'responses':response})
    assert later.mastery.state(tag)['mastery_state']=='INTRODUCED' # Recall is not reviewed understanding.


def test_coverage_reports_states_counts_and_missing_bank(engine):
    add(engine,'attempt','SQL-LOAN-001',passed=False)
    matrix=engine.mastery.coverage(PROBLEMS);s=next(r for r in matrix['concepts'] if r['concept']==TAG)
    assert s['failed_attempts']==1 and s['correct_attempts']==0 and s['problems_attempted']==1
    assert len(matrix['concepts'])==len(CONCEPTS)
    python=next(r for r in matrix['concepts'] if r['concept']=='python.language.functions')
    assert python['mastery_state']=='UNSEEN' and python['problems_available']==[]
    assert 'percentage' not in matrix and all('percentage' not in r for r in matrix['concepts'])


def test_advanced_recommendation_keeps_target_concepts_hidden(engine):
    add(engine,'applied','SQL-LOAN-001')
    engine.clock=lambda:T0+timedelta(days=2)
    assert engine.recommend('LEARN')['kind']=='recall'
    advanced=engine.recommend('INTERVIEW')
    assert advanced['kind']!='recall' and 'concept' not in advanced and 'concepts' not in advanced
