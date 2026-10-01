from trainer.execution.compare import compare


def test_date_contract_rejects_a_formatted_varchar():
    result={'ok':True,'columns':['day'],'types':['VARCHAR'],'rows':[['2026-10-01']]}
    assert not compare(result,['day'],[['2026-10-01']],expected_types=['DATE'])[0]
    result['types']=['DATE']
    assert compare(result,['day'],[['2026-10-01']],expected_types=['DATE'])[0]


def test_timestamp_offsets_normalize_but_naive_and_aware_do_not_match():
    result={'ok':True,'columns':['at'],'types':['TIMESTAMP WITH TIME ZONE'],'rows':[['2026-10-01T09:00:00+09:00']]}
    assert compare(result,['at'],[['2026-10-01T00:00:00Z']],expected_types=['TIMESTAMPTZ'])[0]
    assert not compare(result,['at'],[['2026-10-01T00:00:00']],expected_types=['TIMESTAMPTZ'])[0]
