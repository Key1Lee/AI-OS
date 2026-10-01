import copy
from datetime import date,datetime,timedelta,timezone

import pytest
from pydantic import ValidationError

from trainer.adaptive.selection import readiness,recommend
from trainer.config import ROOT
from trainer.execution.compare import compare
from trainer.mastery.policy import advance,empty_state
from trainer.schemas.models import Exercise,ReasoningEvidence,Table

NOW=datetime(2026,10,1,tzinfo=timezone.utc)


def test_bank_has_original_versioned_coverage_and_hidden_cases(bank):
    assert len(bank.exercises)>=10
    assert {'sql.joins','sql.windows','sql.deduplication','sql.aggregation','sql.temporal','sql.retention','sql.nulls'}.issubset({c for e in bank.exercises.values() for c in e.competencies})
    for exercise in bank.exercises.values():
        assert exercise.hidden_cases
        assert any(c.id=='empty' for c in exercise.hidden_cases)
        public=exercise.public()
        assert not {'hidden_cases','expected_rows','reference_solution','hints','solution_explanation'}&set(public)


def test_schema_rejects_bad_shapes_and_unknown_fields(bank):
    with pytest.raises(ValidationError):
        Table.model_validate({'name':'items','columns':[{'name':'id','type':'INTEGER'}],'rows':[[1,2]]})
    raw=bank.exercises['sql-order-reconciliation'].model_dump()
    raw['hidden_cases'][0]['tables'][0]['columns'][0]['name']='changed'
    with pytest.raises(ValidationError):Exercise.model_validate(raw)


@pytest.mark.parametrize('actual,expected,passed',[
    ([[1],[1]],[[1],[2]],False),
    ([[2],[1]],[[1],[2]],True),
    ([[None]],[[None]],True),
    ([[None]],[[0]],False),
    ([[0.3000000001]],[[0.3]],True),
    ([[True]],[[1]],False),
    ([[date(2026,10,1)]],[['2026-10-01']],True),
    ([],[],True),
])
def test_result_comparator(actual,expected,passed):
    assert compare({'ok':True,'columns':['value'],'rows':actual},['value'],expected)[0] is passed


def test_order_schema_and_float_matching():
    result={'ok':True,'columns':['value'],'rows':[[2],[1]]}
    assert not compare(result,['other'],[[1],[2]])[0]
    assert not compare(result,['value'],[[1],[2]],ordered=True)[0]
    assert compare({'ok':True,'columns':['x'],'rows':[[1],[1.0015]]},['x'],[[1.001],[1]],tolerance=.001)[0]


def evidence(index,*,passed=True,independent=True,difficulty=3,family=None):
    return dict(attempt_id=str(index),exercise_id=f'e{index}',family=family or f'f{index}',difficulty=difficulty,passed=passed,independent=independent,hints=0,solution_seen=False,external_assistance=False)


def test_mastery_requires_transfer_and_later_retest():
    state=advance(empty_state(),evidence(1),0,NOW)
    assert state['level']==2
    state=advance(state,evidence(2,family='f1'),0,NOW+timedelta(hours=1))
    assert state['level']==2
    state=advance(state,evidence(3,difficulty=4),0,NOW+timedelta(hours=2))
    assert state['level']==3
    state=advance(state,evidence(4,difficulty=4),0,NOW+timedelta(days=8))
    assert state['level']==4
    assert state['recent_attempts'][-1]['cold_transfer']
    state=advance(state,evidence(5,passed=False,independent=False),1,NOW+timedelta(days=9))
    assert state['level']==2 and state['trend']=='reopened'
    assert len(state['independent_successes'])==4


def test_hints_repeats_and_assisted_work_cannot_award_independence():
    state=empty_state()
    for i in range(5):state=advance(state,evidence(i,independent=False),0,NOW+timedelta(days=i))
    assert state['level']==2 and state['independent_successes']==[]
    state=advance(state,evidence(10),0,NOW+timedelta(days=6))
    state=advance(state,evidence(10),0,NOW+timedelta(days=7))
    assert len(state['independent_successes'])==1


def test_review_shortens_after_repeated_failure():
    state=advance(empty_state(),evidence(1,passed=False,independent=False),1,NOW)
    assert datetime.fromisoformat(state['next_review'])==NOW+timedelta(days=1)
    state=advance(state,evidence(2,passed=False,independent=False),1,NOW)
    assert datetime.fromisoformat(state['next_review'])==NOW+timedelta(hours=12)


def test_selection_is_stable_and_transfers_recent_gap(bank):
    states={key:empty_state() for key in bank.competencies}
    first=recommend(bank,states,[],NOW)
    assert first==recommend(bank,states,[],NOW)
    history=[dict(exercise_id='sql-customer-latest',difficulty=3,result={'outcome':'Incorrect','independent':False})]
    for key in ['sql.windows','sql.deduplication','sql.nulls']:
        states[key]=advance(states[key],{**evidence(1,passed=False,independent=False,family='crm-current-record'),'exercise_id':'sql-customer-latest'},1,NOW)
    recommendation=recommend(bank,states,history,NOW)
    assert recommendation['exercise_id']!='sql-customer-latest'
    assert recommendation['factors']['transfer']>0
    assert recommendation['difficulty']<=3
    assert readiness([*history,*history])==2


def test_configurable_selection_filters_and_prerequisites(bank):
    states={key:empty_state() for key in bank.competencies}
    assert recommend(bank,states,[],NOW,difficulty=6) is None
    assert recommend(bank,states,[],NOW,competency='sql.retention') is None
    row=recommend(bank,states,[],NOW,competency='sql.retention',practice=True)
    assert row['exercise_id']=='sql-day-seven-retention'
