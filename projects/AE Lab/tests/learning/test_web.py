import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import pytest
from lab.web import create_server
from lab.problems import PROBLEM_MAP,PROBLEMS

@pytest.fixture
def web(tmp_path):
    server=create_server(tmp_path/'web',0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server
    server.shutdown();server.server_close();server.app.executor.shutdown(wait=True);thread.join()


def call(server,path,body=None,token=True):
    url=f'http://127.0.0.1:{server.server_port}{path}'
    req=Request(url,data=json.dumps(body).encode() if body is not None else None,
      headers={'Content-Type':'application/json',**({'X-Lab-Token':server.app.token} if token else {})})
    try:
        with urlopen(req) as res:return res.status,json.loads(res.read())
    except HTTPError as e:return e.code,json.loads(e.read())


def action(web,r,verb,answer):
    status,job=call(web,'/api/learning/actions',{'run_id':r['run_id'],'step':r['learning_step'],'attempt_count':r['attempt_count'],'action':verb,'answer':answer})
    assert status==202
    end=time.monotonic()+10
    while job['status']=='running':
        assert time.monotonic()<end
        time.sleep(.025);job=call(web,'/api/jobs/'+job['id'])[1]
    assert job['status']=='done',job
    return job['result']


def test_learning_ui_api_stale_guard_and_original_catalog(web):
    assert call(web,'/api/catalog')[0]==200 and len(call(web,'/api/catalog')[1]['cases'])==10
    status,cat=call(web,'/api/learning/catalog?mode=INTERVIEW')
    assert status==200 and len(cat['problems'])==len(PROBLEMS) and 'skills_tested' not in json.dumps(cat)
    assert 'solution' not in json.dumps(cat) and 'hidden_tests' not in json.dumps(cat)
    assert call(web,'/api/learning/sessions',{'problem_id':'SQL-LOAN-001'},token=False)[0]==403
    status,r=call(web,'/api/learning/sessions',{'problem_id':'MODEL-GRAIN-001'})
    assert status==201 and 'solution' not in json.dumps(r)
    assert call(web,'/api/bootstrap')[1]['sessions']==[] # Legacy UI cannot dispatch new-format sessions.
    r=action(web,r,'predict',{'prediction':'Delivery and transaction identities may differ.'})
    assert r['learning_step']==1
    assert call(web,'/api/learning/actions',{'run_id':r['run_id'],'step':0,'attempt_count':0,'action':'predict','answer':{}})[0]==409
    r=action(web,r,'prepare',{'requirements':'Stable version and transaction identities.','proposal':'Declare producer and consumer grain.',
                            'input_grain':'Received event.','output_grain':'Logical transaction.'})
    p=PROBLEM_MAP[r['problem_id']]
    a={k:v[0] for k,v in p['evaluation_rules']['expected'].items()}|{'reason':'The physical delivery key differs from a transaction identity.'}
    r=action(web,r,'submit',a)
    assert r['status']=='PASS' and r['learning_step']==3
    assert call(web,'/api/learning/sessions/'+r['run_id'])[1]==r
    assert call(web,'/api/learning/coverage')[1]['concepts']
    assert call(web,'/api/learning/recommend')[0]==200
    for path in ('/learn','/learning.js','/learning.css'):
        with urlopen(f'http://127.0.0.1:{web.server_port}{path}') as response:assert response.status==200


def test_bad_types_and_cross_surface_sessions_fail_cleanly(web):
    for pid in ([],True,'MISSING'):
        assert call(web,'/api/learning/sessions',{'problem_id':pid})[0]==409
    legacy=call(web,'/api/sessions',{})[1]
    assert call(web,'/api/learning/sessions/'+legacy['run_id'])[0]==404
    assert call(web,'/api/learning/catalog?mode=missing')[0]==404


def test_original_cli_preserves_inspection_and_refuses_new_record_mutations(tmp_path,capsys):
    from lab.cli import main
    from lab.learning_engine import LearningEngine
    from lab.store import Store
    root=tmp_path/'cli';engine=LearningEngine(Store(root));r=engine.start('MODEL-GRAIN-001')
    assert main(['--state-dir',str(root),'inspect',r['run_id']])==0
    assert r['run_id'] in capsys.readouterr().out
    assert main(['--state-dir',str(root),'verify',r['run_id']])==1
    assert 'lab-learn' in capsys.readouterr().err
    assert engine.store.get(r['run_id'])['state']=='READY'


def test_legacy_bootstrap_never_routes_to_a_learning_job(web):
    r=web.app.learning.start('MODEL-GRAIN-001')
    web.app.job={'id':'isolated-metadata-probe','run_id':r['run_id'],'status':'running','action':'submit'}
    boot=call(web,'/api/bootstrap')[1]
    assert boot['sessions']==[] and boot['job'] is None
    assert call(web,'/api/learning/bootstrap')[1]['sessions'][0]['run_id']==r['run_id']


def test_business_focus_public_assessment_and_trusted_tutor_boundary(web):
    status,cat=call(web,'/api/learning/catalog?focus=reasoning')
    assert status==200 and len(cat['problems'])==60
    assert len(call(web,'/api/learning/catalog?focus=sql')[1]['problems'])==120
    assert call(web,'/api/learning/recommend?focus=reasoning')[1]['problem_id']=='REASON-TRANSLATE-001'
    assert call(web,'/api/learning/catalog?focus=invalid')[0]==404
    status,r=call(web,'/api/learning/sessions',{'problem_id':'REASON-TRANSLATE-001','mode':'INTERVIEW'})
    assert status==201 and 'workbook' not in r['problem']['artifacts']
    r=action(web,r,'predict',{'prediction':'Which board decision does the requested number support?'})
    assert r['clarifications'][0]['status']=='PENDING_TUTOR_REVIEW'
    assert not r['hints'] and r['hint_limit']==0
    assert 'expected' not in json.dumps(r['problem']['artifacts']['workbook'])
    r=action(web,r,'ask',{'question':'What is the producer business identity guarantee?'})
    assert len(r['clarifications'])==2
    assert call(web,'/api/learning/review',{'run_id':r['run_id'],'criteria':{'all':True}})[0]==404
    assert call(web,'/api/learning/respond',{'run_id':r['run_id'],'category':'essential'})[0]==404
    job=call(web,'/api/learning/actions',{'run_id':r['run_id'],'step':r['learning_step'],'attempt_count':0,'action':'respond','answer':{}})[1]
    end=time.monotonic()+5
    while job['status']=='running':
        assert time.monotonic()<end
        time.sleep(.025);job=call(web,'/api/jobs/'+job['id'])[1]
    assert job['status']=='failed'
    with urlopen(f'http://127.0.0.1:{web.server_port}/reasoning.js') as response:assert response.status==200
