"""Real loopback API journey; every successful engine result comes from its SDK."""
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from lab.web import create_server, resume_step, session_view

@pytest.fixture
def web(tmp_path):
    server = create_server(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    server.app.executor.shutdown(wait=True)
    thread.join()

def call(web, path, body=None, *, token=True, origin=None, host=None):
    headers = {}
    if body is not None:
        headers.update({'Content-Type':'application/json', 'X-Lab-Token':web.app.token if token else 'bad'})
    if origin:
        headers['Origin'] = origin
    if host:
        headers['Host'] = host
    request = Request(f'http://127.0.0.1:{web.server_port}{path}',
                      data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as exc:
        response = exc
    with response:
        data = response.read()
        return response.status, json.loads(data) if response.headers.get_content_type() == 'application/json' else data.decode()

def action(web, session, action, answer=None, *, expect_failure=False):
    status, job = call(web, '/api/actions', {'run_id':session['run_id'], 'step':session['step'], 'action':action, 'answer':answer or {}})
    assert status == 202, job
    if action == 'run':
        duplicate_status, _ = call(web, '/api/actions', {'run_id':session['run_id'], 'step':session['step'], 'action':action})
        assert duplicate_status == 409
    deadline = time.monotonic() + 90
    while job['status'] == 'running':
        assert time.monotonic() < deadline, 'Native action did not finish'
        time.sleep(.1)
        status, job = call(web, '/api/jobs/' + job['id'])
        assert status == 200
    if expect_failure:
        assert job['status'] == 'failed'
        return call(web, '/api/sessions/' + session['run_id'])[1]
    assert job['status'] == 'done', job
    return job['result']

def test_http_nine_step_native_learning_disclosure_recovery_and_reload(web):
    status, session = call(web, '/api/sessions', {})
    assert status == 201 and session['step'] == 0 and session['evidence'] == {}
    assert 'diagnosis' not in json.dumps(session)
    session = action(web, session, 'continue')
    assert session['step'] == 1
    session = action(web, session, 'predict', {'rows':1000})
    assert session['step'] == 2 and session['evidence'] == {} and session['feedback'] == {}
    session = action(web, session, 'run')
    assert session['step'] == 3
    assert session['evidence']['fault']['rows'] == 1700
    assert session['evidence']['fault']['publication'] == 'BLOCKED'
    assert session['feedback']['predict']['outcome'] == 'fail'
    assert call(web, '/api/sessions/' + session['run_id'])[1] == session
    session = action(web, session, 'continue')
    session = action(web, session, 'diagnose', {'layer':'quality','property':'freshness','signal':'null_values'})
    assert session['step'] == 4 and session['feedback']['diagnose']['outcome'] == 'fail'
    unchanged = action(web, session, 'fix', {'repair':'upsert'}, expect_failure=True)
    assert unchanged['step'] == 4
    session = action(web, session, 'diagnose', {'layer':'ingestion','property':'idempotency','signal':'duplicate_order_ids'})
    assert session['step'] == 5
    unchanged = action(web, session, 'fix', {'repair':'append'}, expect_failure=True)
    assert unchanged['step'] == 5
    session = action(web, session, 'fix', {'repair':'upsert'})
    assert session['step'] == 6 and session['evidence']['recovery']['rows'] == 1000
    session = action(web, session, 'verify')
    assert session['step'] == 7 and all(session['verification']['checks'].values())
    session = action(web, session, 'recall', {'rows':1700,'key':'customer_id','repair':'append'})
    assert session['step'] == 7 and session['state'] == 'VERIFIED'
    session = action(web, session, 'recall', {'rows':1000,'key':'order_id','repair':'upsert'})
    assert session['step'] == 8
    session = action(web, session, 'continue')
    assert session['step'] == 9 and session['state'] == 'MASTERED'
    assert session['evidence']['fault']['rows'] == 1700
    assert session['evidence']['rerun']['rows'] == 1000
    assert call(web, '/api/sessions/' + session['run_id'])[1] == session
    status, second = call(web, '/api/sessions', {})
    assert status == 201 and second['run_id'] != session['run_id']
    assert call(web, '/api/sessions/' + session['run_id'])[1]['step'] == 9

def test_local_server_identity_static_assets_and_request_guards(web):
    assert call(web, '/api/health')[1]['app'] == 'ae-lab-browser-v1'
    assert call(web, '/')[0] == call(web, '/app.js')[0] == call(web, '/style.css')[0] == 200
    assert 'Learn by tracing' in call(web, '/')[1]
    assert call(web, '/api/sessions', {}, token=False)[0] == 403
    assert call(web, '/api/sessions', {}, origin='https://example.com')[0] == 403
    assert call(web, '/api/bootstrap', host='evil.example')[0] == 403
    assert call(web, '/../../README.md')[0] == 404
    assert call(web, '/api/sessions/missing')[0] == 404
    session = call(web, '/api/sessions', {})[1]
    assert call(web, '/api/actions', {'run_id':session['run_id'],'step':8,'action':'continue'})[0] == 409
    assert call(web, '/api/actions', {'run_id':session['run_id'],'step':True,'action':'continue'})[0] == 409

def test_interrupted_recovery_and_latest_verification_resume_at_required_action(web):
    record = web.app.lab.start()
    record.update(state='REMEDIATED',learning_step=5)
    assert resume_step(record) == 5
    record['phases']['recovery'] = {}
    assert resume_step(record) == 6
    record.update(state='VERIFIED',learning_step=8,verification={'status':'RUNNING','checks':{}})
    assert resume_step(record) == 6
    record.update(state='MASTERED',learning_step=7,verification={'status':'PASS','checks':{}})
    assert resume_step(record) == 8
    record.update(state='DIAGNOSING',learning_step=4)
    record['answers']['diagnose'] = [{'evaluation':{'outcome':'fail'}}]
    assert resume_step(record) == 4
    record['answers']['diagnose'] = [{'evaluation':{'outcome':'pass'}}]
    assert resume_step(record) == 5
