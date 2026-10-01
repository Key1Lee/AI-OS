from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from data_system_map.security import redact
from trainer.data_map.contracts import COMMERCE_SCENARIO, EnginePort
from trainer.data_map.store import InvestigationStore, MapConflict


def now():
    return datetime.now(timezone.utc).isoformat()


class InvestigationService:
    """Scoring/visibility policy over normalized evidence, not adapter internals."""

    def __init__(self, store: InvestigationStore, engine: EnginePort):
        self.store, self.engine = store, engine

    def _public(self, value):
        if value:
            value['scenario'] = {key: COMMERCE_SCENARIO[key] for key in ['id', 'title', 'brief']} if value['system_id']==COMMERCE_SCENARIO['system_id'] else {
                'id':'map-exploration-v1','title':'Explore this imported system','brief':'Inspect declared metadata and recorded evidence. This system has no authored grading contract.'}
            relevant = {'model.commerce.stg_orders','model.commerce.int_order_items','model.commerce.fct_orders'}
            first = next((a for a in value['actions'] if a['target'] in relevant and a['kind'] not in {'hypothesis'}), None)
            seconds = max(0,(datetime.fromisoformat(first['created_at'])-datetime.fromisoformat(value['started_at'])).total_seconds()) if first else None
            value['telemetry'] = {'recorded_tests_inspected': sum(a['kind']=='tests' for a in value['actions']), 'tests_executed':0,
                                  'time_to_relevant_evidence_seconds':seconds,
                                  'verification_performed':False, 'note':'Recorded artifact inspection is not a new dbt execution.'}
        return value

    def current(self):
        with self.store.connection() as connection:
            row = connection.execute('SELECT * FROM sessions WHERE status="active"').fetchone()
            return self._public(self.store.view(connection,row)) if row else None

    def get(self, key):
        with self.store.connection() as connection:
            return self._public(self.store.view(connection,connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()))

    def history(self):
        with self.store.connection() as connection:
            return [{'id':r['id'],'mode':r['mode'],'status':r['status'],'started_at':r['started_at'],'result':json.loads(r['result']) if r['result'] else None} for r in connection.execute('SELECT * FROM sessions ORDER BY started_at DESC,id')]

    def policy(self, system_id):
        current = self.current()
        if current and current['mode']=='assessment':
            return {'reveal_diagnostics':False, 'snapshot_id':current['snapshot_id'] if current['system_id']==system_id else None, 'audience':'assessment'}
        return {'reveal_diagnostics':bool(current and current['system_id']==system_id and current['mode']=='learning'),
                'snapshot_id':current['snapshot_id'] if current and current['system_id']==system_id else None, 'audience':'learning' if current else 'explore'}

    def start(self, system_id, mode):
        if mode not in {'learning','assessment'}:
            raise MapConflict('Choose Learning or Assessment.')
        if mode=='assessment' and system_id!=COMMERCE_SCENARIO['system_id']:
            raise MapConflict('Only the original commerce demonstration has an authored assessment in this release.')
        snapshot = self.engine.snapshot(system_id)
        with self.store.connection(write=True) as connection:
            current = connection.execute('SELECT * FROM sessions WHERE status="active"').fetchone()
            if current and current['mode']=='assessment':
                if current['system_id']==system_id and mode=='assessment':
                    return self._public(self.store.view(connection,current))
                raise MapConflict('Finish the active assessment or explicitly end it and learn before changing mode.')
            if current and current['system_id']==system_id and current['mode']==mode:
                return self._public(self.store.view(connection,current))
            if current:
                connection.execute('UPDATE sessions SET status="completed",completed_at=? WHERE id=?',(now(),current['id']))
            exposed = connection.execute('SELECT 1 FROM sessions WHERE system_id=? LIMIT 1',(system_id,)).fetchone()
            identity = uuid4().hex
            connection.execute('INSERT INTO sessions(id,system_id,snapshot_id,mode,status,started_at,independent,draft) VALUES(?,?,?,?,"active",?,?,?)',
                               (identity,system_id,snapshot.snapshot_id,mode,now(),int(mode=='assessment' and not exposed),'{}'))
            return self._public(self.store.view(connection,connection.execute('SELECT * FROM sessions WHERE id=?',(identity,)).fetchone()))

    def action(self, system_id, kind, target=None, payload=None):
        current = self.current()
        if not current:
            current = self.start(system_id,'learning')
        if current['system_id']!=system_id:
            raise MapConflict('The active investigation belongs to another system. Finish it before inspecting this system.')
        with self.store.connection(write=True) as connection:
            row = connection.execute('SELECT * FROM sessions WHERE id=? AND status="active"',(current['id'],)).fetchone()
            if row is None:
                raise MapConflict('This investigation ended. Reload its saved state.')
            if connection.execute('SELECT COUNT(*) FROM actions WHERE session_id=?',(row['id'],)).fetchone()[0]>=10000:
                raise MapConflict('The investigation action limit has been reached. Save your diagnosis and finish.')
            connection.execute('INSERT INTO actions(session_id,kind,target,payload,created_at) VALUES(?,?,?,?,?)', (row['id'],kind,target,json.dumps(payload or {},allow_nan=False),now()))
        return self.get(current['id'])

    def save(self, key, draft, revision):
        with self.store.connection(write=True) as connection:
            row = connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()
            if row is None:
                raise KeyError(key)
            if row['status']!='active' or row['revision']!=revision:
                raise MapConflict('This investigation draft changed or ended. Your browser copy is retained; reload the saved version before writing.')
            connection.execute('UPDATE sessions SET draft=?,revision=revision+1 WHERE id=?',(json.dumps(draft),key))
        return self.get(key)

    def hypothesis(self, key, content):
        current = self.current()
        if not current or current['id']!=key:
            raise MapConflict('Only the active investigation can record a hypothesis.')
        return self.action(current['system_id'],'hypothesis',payload={'text':redact(content),'classification':'INFERENCE','author':'candidate','validated':False})

    def end(self, key, *, learn=False):
        with self.store.connection(write=True) as connection:
            row = connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()
            if row is None:
                raise KeyError(key)
            if row['status']!='active':
                raise MapConflict('Only an active investigation can be ended.')
            connection.execute('UPDATE sessions SET status=?,completed_at=?,independent=0 WHERE id=?',('abandoned' if row['mode']=='assessment' else 'completed',now(),key))
            connection.execute('INSERT INTO actions(session_id,kind,payload,created_at) VALUES(?,?,?,?)',(key,'ended_and_learned' if learn else 'ended','{}',now()))
            system_id = row['system_id']
        return self.start(system_id,'learning') if learn else self.get(key)

    def submit(self, key, answer):
        current = self.get(key)
        if current['system_id'] != COMMERCE_SCENARIO['system_id']:
            raise MapConflict('This imported system has no authored grading contract. Its inspection history and drafts remain available.')
        snapshot = self.engine.snapshot(current['system_id'],current['snapshot_id'])
        valid_nodes = {node.id for node in snapshot.nodes if node.node_type!='test'}
        if answer['observed_failure'] not in valid_nodes or answer['suspected_origin'] not in valid_nodes or not set(answer['affected_outputs']).issubset(valid_nodes):
            raise MapConflict('Select nodes from the frozen investigation graph.')
        body = json.dumps(answer,sort_keys=True)
        with self.store.connection(write=True) as connection:
            prior = connection.execute('SELECT * FROM submissions WHERE request_id=?',(answer['request_id'],)).fetchone()
            if prior:
                if prior['session_id']!=key or prior['body']!=body:
                    raise MapConflict('This request ID belongs to a different diagnosis.')
                return self._public(self.store.view(connection,connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()))
            row = connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()
            if row['status']!='active':
                raise MapConflict('This investigation is complete. Its evidence cannot be overwritten.')
            saved = self.store.view(connection,row)
            actions = saved['actions']
            has = lambda kind, target: any(a['kind']==kind and a['target']==target for a in actions)
            scenario = COMMERCE_SCENARIO
            expected_outputs = {item['id'] for item in self.engine.impact(current['system_id'],scenario['failure'],snapshot_id=current['snapshot_id'])['affected_outputs']}
            checks = [
                ('Located the observed failure',answer['observed_failure']==scenario['failure']),
                ('Selected the evidence-supported suspicion',answer['suspected_origin']==scenario['suspect']),
                ('Named the declared order grain',answer['grain']==scenario['grain']),
                ('Inspected direct upstream lineage',has('upstream',scenario['failure']) or has('upstream',scenario['suspect'])),
                ('Inspected relevant schema',has('schema',scenario['suspect']) or has('schema',scenario['failure'])),
                ('Inspected the failed recorded test',has('tests',scenario['failure'])),
                ('Opened the intermediate SQL',has('sql',scenario['suspect'])),
                ('Assessed business-output impact',set(answer['affected_outputs'])==expected_outputs and (has('impact',scenario['failure']) or has('downstream',scenario['failure']))),
            ] if current['system_id']==scenario['system_id'] else []
            result = {'classification':'FACT','policy_version':'map-investigation-v1','score':sum(ok for _,ok in checks),'total':len(checks),
                      'checks':[{'label':label,'satisfied':ok} for label,ok in checks], 'independent':saved['independent'],
                      'unassessed':['Root-cause proof','Fix validity','Verification-plan quality','Explanation quality'],
                      'feedback':'Scores reflect authored answer selections and recorded inspection actions. They do not establish a verified repair or broad mastery.',
                      'answer':answer, 'tests_executed':0, 'verification_performed':False}
            stamp = now()
            connection.execute('INSERT INTO submissions VALUES(?,?,?,?)',(answer['request_id'],key,body,json.dumps(result)))
            connection.execute('UPDATE sessions SET status="completed",completed_at=?,draft=?,result=? WHERE id=?',(stamp,body,json.dumps(result),key))
            connection.execute('INSERT INTO actions(session_id,kind,payload,created_at) VALUES(?,?,?,?)',(key,'diagnosis_submitted','{}',stamp))
            return self._public(self.store.view(connection,connection.execute('SELECT * FROM sessions WHERE id=?',(key,)).fetchone()))
