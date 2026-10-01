"""Guard the full row-limit behavior and ambiguous floating matches."""
from trainer.execution.compare import compare


def test_duplicate_multiset_at_1000_row_limit_does_not_recurse():
    result={'ok':True,'columns':['value'],'rows':[[1]]*1000}
    assert compare(result,['value'],[[1]]*1000)[0]
    assert not compare(result,['value'],[[1]]*999+[[2]])[0]


def test_non_greedy_floating_assignment():
    result={'ok':True,'columns':['x'],'rows':[[1],[1.0015]]}
    assert compare(result,['x'],[[1.001],[1]],tolerance=.001)[0]
