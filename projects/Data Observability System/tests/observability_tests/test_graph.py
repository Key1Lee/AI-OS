import pytest

from data_system_map.contracts import DataEdge,DataNode,GraphSnapshot,Provenance
from data_system_map.graph import Graph


def golden(pairs):
    return Graph(GraphSnapshot(system_id='golden',name='Golden graph',nodes=[DataNode(id=n,name=n,node_type='model') for n in 'ABCDEF'],
        edges=[DataEdge(id=f'{a}-{b}',from_node=a,to_node=b,evidence_source=Provenance(source='golden',pointer='/edges')) for a,b in pairs]))


def test_branched_golden_graph():
    graph=golden([('A','B'),('B','C'),('C','D'),('A','E'),('E','D')])
    assert graph.upstream('D')==['A','B','C','E']
    assert graph.downstream('A')==['B','C','D','E']
    assert graph.direct_parents('D')==['C','E']
    assert graph.direct_children('A')==['B','E']
    assert graph.shortest_path('A','D')==['A','E','D']
    assert graph.all_paths('A','D')=={'paths':[['A','B','C','D'],['A','E','D']],'truncated':False}
    assert graph.impact('A')=={'direct':['B','E'],'transitive':['C','D'],'affected_outputs':[]}
    assert graph.cycles()==[]


def test_cycles_disconnected_and_self_paths_terminate():
    graph=golden([('A','B'),('B','C'),('C','A'),('C','D')])
    assert graph.cycles()==[['A','B','C','A']]
    assert graph.upstream('A')==['B','C']
    assert graph.downstream('A')==['B','C','D']
    assert graph.shortest_path('F','D') is None
    assert graph.all_paths('F','D')['paths']==[]
    assert graph.shortest_path('A','A')==['A']
    assert graph.all_paths('A','D')['paths']==[['A','B','C','D']]


def test_path_limits_and_unknown_ids():
    graph=golden([('A','B'),('B','D'),('A','C'),('C','D')])
    assert graph.all_paths('A','D',limit=1)['truncated']
    assert graph.all_paths('A','D',max_depth=2)['truncated']
    with pytest.raises(KeyError):graph.downstream('missing')
    with pytest.raises(ValueError):graph.all_paths('A','D',limit=0)


def test_test_association_is_not_data_dependency():
    graph=golden([('A','B')])
    graph.snapshot.edges.append(DataEdge(id='A-test',from_node='A',to_node='F',relationship_type='tests',evidence_source=Provenance(source='fixture',pointer='/')))
    assert Graph(graph.snapshot).direct_children('A')==['B']
