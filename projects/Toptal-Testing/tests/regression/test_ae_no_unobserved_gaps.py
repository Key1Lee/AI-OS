from tests.ae.test_workflow import start,submit


def test_syntax_error_does_not_claim_untested_concept_gaps(ae_factory):
    client,_=ae_factory();attempt=start(client)
    response=submit(client,attempt,'SELECT FROM invalid syntax')
    assert response.status_code==200
    assert response.json()['result']['outcome']=='Incorrect'
    states={c['id']:c for c in client.get('/api/competencies').json()}
    assert states['sql.execution']['level']==1
    for key in ['sql.joins','sql.aggregation','sql.nulls','modeling.grain']:
        assert states[key]['level']==0 and states[key]['attempts']==0
    assert {m['competency_id'] for m in client.get('/api/mistakes').json()}=={'sql.execution'}
