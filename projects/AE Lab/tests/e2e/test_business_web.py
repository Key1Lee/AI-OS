"""Exercise every new business case over HTTP and unchanged native runtimes."""
import json
import sqlite3
import time

import pytest

from test_web import web, call, action
from lab.business_catalog import CASES
from lab.cli import main

# Independent expected outcomes for the ten authored stories, not derived by SQL.
OUTCOMES = [(4,150,2,75),(2,220,4,440),(2,17,1,5),(2,10,4,24),(3,250,2,150),
            (2,150,2,120),(3,3,2,2),(1,700,1,100),(2,150,2,40),(1,100,3,300)]

@pytest.mark.parametrize('item,outcome',list(zip(CASES,OUTCOMES)),ids=[c['id'] for c in CASES])
def test_distinct_business_native_http_journey(web,item,outcome,capsys):
    status,session=call(web,'/api/sessions',{'scenario_id':item['id']})
    assert status==201 and session['step']==0 and session['evidence']=={}
    assert session['case']['title']==item['title']
    assert not any(key in session['case'] for key in ('expected','sql','why','tradeoff','predict','fix','recall'))
    session=action(web,session,'continue')
    assert 'predict' in session['case'] and 'correct' not in session['case']['predict']
    session=action(web,session,'predict',{'choice':'wrong'})
    assert session['step']==2 and not session['feedback'] and not session['evidence']
    session=action(web,session,'run')
    fault=session['evidence']['fault']
    assert (fault['row_count'],fault['value'])==outcome[:2]
    assert fault['model_status']=='FAIL' and fault['publication']=='BLOCKED'
    assert call(web,'/api/sessions/'+session['run_id'])[1]==session
    # The bad candidate must not replace the validated healthy release.
    directory=web.app.lab.store.root/session['run_id']
    with sqlite3.connect(directory/'warehouse.sqlite') as db:
        assert db.execute('SELECT phase FROM publication').fetchone()[0]=='baseline'
    session=action(web,session,'continue')
    session=action(web,session,'diagnose',{'choice':'wrong','reason':'Unassessed reflection'})
    assert session['step']==4 and session['feedback']['diagnose']['outcome']=='fail'
    unchanged=action(web,session,'fix',{'choice':item['fix']['correct']},expect_failure=True)
    assert unchanged['step']==4
    session=action(web,session,'diagnose',{'choice':item['diagnose']['correct']})
    assert session['step']==5 and session['case']['why'] and session['case']['tradeoff']
    assert 'recall' not in session['case']
    unchanged=action(web,session,'fix',{'choice':'wrong'},expect_failure=True)
    assert unchanged['step']==5
    session=action(web,session,'fix',{'choice':item['fix']['correct']})
    repaired=session['evidence']['recovery']
    assert (repaired['row_count'],repaired['value'])==outcome[2:]
    assert repaired['quality_status']=='PASS' and all(repaired['checks'].values())
    if item['number']==7:
        assert repaired['quarantine'][0]['entity_id']=='T2'
    session=action(web,session,'verify')
    assert session['step']==7 and all(session['verification']['checks'].values())
    assert session['evidence']['fault']==fault
    session=action(web,session,'recall',{'choice':True})
    assert session['step']==7 and session['feedback']['recall']['outcome']=='fail'
    session=action(web,session,'recall',{'choice':item['recall']['correct']})
    session=action(web,session,'continue')
    assert session['step']==9 and session['state']=='COMPLETED'
    record=web.app.lab.store.get(session['run_id'])
    assert record['answers']['recall'][-1]['evaluation']['provenance']['system']=='Toptal-Testing System'
    assert record['phases']['recovery']['native_quality']['provenance']=='quality_system.engine.validate_bundle'
    assert (directory/'failed.mmd').is_file() and (directory/'evidence.json').is_file()
    if item['number'] in (1,2):
        assert 'class n1 failed' in (directory/'failed.mmd').read_text()
    if item['number']==10:
        assert 'class n5 failed' in (directory/'failed.mmd').read_text()
    assert all(event['scenario_id']==item['id'] for event in record['events'])
    assert call(web,'/api/sessions/'+session['run_id'])[1]==session
    second=call(web,'/api/sessions',{'scenario_id':item['id']})[1]
    assert second['run_id']!=session['run_id'] and second['step']==0
    assert call(web,'/api/sessions/'+session['run_id'])[1]['step']==9
    if item['number']==1:
        state_args=['--state-dir',str(web.app.lab.store.root)]
        assert main([*state_args,'inspect',session['run_id']])==0
        assert 'Sales · USD: 75' in capsys.readouterr().out
        assert main([*state_args,'verify',session['run_id']])==1
        assert 'Resume this business exercise in the browser' in capsys.readouterr().err
        assert call(web,'/api/sessions/'+session['run_id'])[1]['step']==9

def test_catalog_guards_and_pinned_input_resume(web):
    status,catalog=call(web,'/api/catalog')
    assert status==200 and len(catalog['cases'])==10
    assert len({c['concept'] for c in catalog['cases']})==10
    assert 'correct' not in json.dumps(catalog) and 'expected' not in json.dumps(catalog)
    for scenario in ('missing',[],True):
        assert call(web,'/api/sessions',{'scenario_id':scenario})[0]==409
    session=call(web,'/api/sessions',{'scenario_id':CASES[0]['id']})[1]
    session=action(web,session,'continue')
    session=action(web,session,'predict',{'choice':CASES[0]['predict']['correct']})
    path=web.app.lab.store.root/session['run_id']/'fixtures.json'
    source=json.loads(path.read_text())
    source['sales']['rows'][0][2]=500
    path.write_text(json.dumps(source))
    status,job=call(web,'/api/actions',{'run_id':session['run_id'],'step':session['step'],'action':'run'})
    assert status==202
    deadline=time.monotonic()+5
    while job['status']=='running':
        assert time.monotonic()<deadline
        time.sleep(.05)
        job=call(web,'/api/jobs/'+job['id'])[1]
    assert job['status']=='failed' and 'Pinned fixtures changed' in job['error']
    unchanged=call(web,'/api/sessions/'+session['run_id'])[1]
    assert unchanged['step']==2 and unchanged['evidence']=={}
    assert web.app.lab.store.get(session['run_id'])['phases']=={}
