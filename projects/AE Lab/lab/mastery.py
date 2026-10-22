"""Append-only AE learning evidence. No Toptal canonical learner writes."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4
from .curriculum import CONCEPTS, POLICY


def stamp(value):
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    if date.tzinfo is None:raise ValueError('Evidence time must be timezone aware')
    return date.astimezone(timezone.utc)

class Mastery:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS learning_evidence (id TEXT PRIMARY KEY, concept TEXT NOT NULL, document TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS learning_evidence_concept ON learning_evidence(concept)')

    def add(self,concept,kind,problem,at,*,passed=None,assisted=False,reference=None,reviewer=None,note=None,identity=None,error_classes=None):
        if concept not in CONCEPTS or kind not in ('introduced','understood','applied','debugged','recall','attempt'):
            raise ValueError('Unknown learning concept or evidence kind')
        at=stamp(at).isoformat()
        if kind in ('understood','debugged') and (not reviewer or not reference or not note):
            raise ValueError('Causal understanding/debugging needs a reviewer, evidence reference and rationale')
        item={'id':identity or str(uuid4()),'concept':concept,'kind':kind,'problem_id':problem['problem_id'],
              'domain':problem['domain'],'difficulty':problem['difficulty']['level'],'at':at,'passed':passed,
              'assisted':assisted,'reference':reference,'reviewer':reviewer,'note':note,'scope':'AE local learning evidence'}
        if error_classes:item['error_classes']=list(error_classes)
        with self.store.connect() as db:
            old=db.execute('SELECT document FROM learning_evidence WHERE id=?',(item['id'],)).fetchone()
            if old:
                if json.loads(old[0])!=item:raise ValueError('Evidence identity is immutable')
                return item
            db.execute('INSERT INTO learning_evidence VALUES (?,?,?)',(item['id'],concept,json.dumps(item)))
        return item

    def evidence(self,concept=None):
        with self.store.connect() as db:
            query='SELECT document FROM learning_evidence'+(' WHERE concept=?' if concept else '')+' ORDER BY rowid'
            rows=db.execute(query,(concept,) if concept else ()).fetchall()
        return sorted((json.loads(r[0]) for r in rows),key=lambda r:(r['at'],r['id']))

    def state(self,concept,now=None):
        evidence=self.evidence(concept)
        trustworthy=[e for e in evidence if e['passed'] is True and not e['assisted']]
        understood=[e for e in trustworthy if e['kind']=='understood']
        applied=[e for e in trustworthy if e['kind']=='applied']
        debugged=[e for e in trustworthy if e['kind']=='debugged']
        recalls=[e for e in trustworthy if e['kind']=='recall']
        transfer=[]
        for later in applied:
            if any(earlier['problem_id']!=later['problem_id'] and earlier['domain']!=later['domain'] and
                   stamp(later['at'])-stamp(earlier['at'])>=timedelta(days=1) for earlier in applied):
                transfer.append(later)
        # Debug repair must be a task distinct from the earlier application.
        debug_ok=any(a['problem_id']!=d['problem_id'] and stamp(a['at'])<=stamp(d['at']) for a in applied for d in debugged)
        state='UNSEEN'
        if evidence:state='INTRODUCED'
        if understood:state='UNDERSTOOD'
        if understood and applied:state='APPLIED'
        if state=='APPLIED' and debug_ok:state='DEBUGGED'
        if state=='DEBUGGED' and transfer:state='TRANSFERRED'
        tasks={e['problem_id'] for e in applied+debugged};domains={e['domain'] for e in applied+debugged}
        recall_days={stamp(e['at']).date() for e in recalls}
        practice=[stamp(e['at']) for e in applied+debugged+recalls]
        span=(max(practice)-min(practice)).days if practice else 0
        if state=='TRANSFERRED' and len(tasks)>=3 and len(domains)>=2 and len(recall_days)>=2 and span>=7:
            state='MASTERED'
        tested=[e for e in evidence if e['kind'] in ('attempt','recall')]
        attempts=[e for e in evidence if e['kind']=='attempt']
        last=max((e['at'] for e in tested),default=None)
        failed=[e for e in tested if e['passed'] is False]
        consecutive=0
        for e in reversed(tested):
            if e['passed'] is not False:break
            consecutive+=1
        source=max(applied+recalls,key=lambda e:e['at'],default=None)
        intervals=POLICY['recall_intervals_days']
        due=(stamp(source['at'])+timedelta(days=intervals[min(len(recall_days),len(intervals)-1)])).isoformat() if source else None
        if tested and tested[-1]['kind']=='recall' and tested[-1]['passed'] is False:
            due=(stamp(tested[-1]['at'])+timedelta(days=1)).isoformat()
        return {'concept':concept,'mastery_state':state,'transfer_demonstrated':bool(transfer),
                'error_classes':{c:sum(c in e.get('error_classes',[]) for e in attempts) for c in sorted({c for e in attempts for c in e.get('error_classes',[])})},
                'problems_attempted':len({e['problem_id'] for e in attempts}),
                'correct_attempts':sum(e['passed'] is True for e in attempts),
                'failed_attempts':sum(e['passed'] is False for e in attempts),'last_tested':last,
                'consecutive_failures':consecutive,'due_recall':due,'evidence_count':len(evidence),
                'evidence_ids':[e['id'] for e in evidence],
                'gaps':{'causal_understanding':not bool(understood),'application':not bool(applied),'debugging':not debug_ok,
                        'transfer':not bool(transfer),'three_tasks':len(tasks)<3,'two_recall_days':len(recall_days)<2,'seven_day_span':span<7}}

    def coverage(self,problems):
        matrix=[]
        for concept,metadata in CONCEPTS.items():
            available=[p for p in problems if concept in p['mastery_tags']]
            matrix.append({**self.state(concept),'domain':metadata['domain'],'difficulty':sorted({p['difficulty']['level'] for p in available}),
                           'problems_available':[p['problem_id'] for p in available]})
        return {'contract_version':'ae-coverage-v1','authority':'AE-local evidence, separate from Toptal examination records','concepts':matrix}

    def select(self,problems,now,mode='LEARN',exclude=(),initial_level=2):
        """Bounded deterministic selection. Return a gap instead of fake content."""
        when=stamp(now);candidates=[p for p in problems if mode in p['modes'] and p['problem_id'] not in exclude]
        if not candidates:return {'kind':'gap','reason':'No problem supports this mode and context.'}
        states={c:self.state(c) for c in CONCEPTS}
        relevant={t for p in candidates for t in p['mastery_tags']}
        all_evidence=self.evidence(); tested=[e for e in all_evidence if e['kind']=='attempt' and e['concept'] in relevant]
        last=max(tested,key=lambda e:e['at'],default=None)
        successful=[e for e in tested if e['passed'] and not e['assisted']]
        target=min(6,max((int(e['difficulty'][1]) for e in successful),default=initial_level-1)+1)
        # Active recall precedes another full problem; only authored relevant prompts.
        due=[]
        for p in candidates:
            for tag in p['mastery_tags']:
                s=states[tag]
                if mode in ('LEARN','PRACTICE') and s['due_recall'] and stamp(s['due_recall'])<=when and any(tag in q.get('concepts',p['mastery_tags']) for q in p['recall']):
                    due.append((s['due_recall'],p['problem_id'],tag))
        if due:
            deadline,pid,tag=min(due)
            return {'kind':'recall','problem_id':pid,'concept':tag,'due_at':deadline,'reason':'A short recall check is due.'}
        weak={c for c,s in states.items() if c in relevant and s['consecutive_failures']>0}
        if weak and last:
            different=[p for p in candidates if p['domain']!=last['domain'] and p['problem_id']!=last['problem_id'] and weak & set(p['mastery_tags'])]
            if different:
                # Move down a level after repeated misses, while retaining a different business mechanism.
                ceiling=max(1,int(last['difficulty'][1])-(1 if max(states[t]['consecutive_failures'] for t in weak)>=2 else 0))
                suitable=[p for p in different if int(p['difficulty']['level'][1])<=ceiling]
                if not suitable:
                    return {'kind':'gap','reason':'No simpler different-domain example exists at the required level yet.',
                            'target_level':f'L{ceiling}','concepts':sorted(weak)}
                p=min(suitable,key=lambda p:(p['transfer_from']!=last['problem_id'],-len(weak & set(p['mastery_tags'])),p['problem_id']))
                return {'kind':'problem','problem_id':p['problem_id'],'reason':'A weak concept returns in a different business context.','target_level':f'L{ceiling}'}
            # Repeating a renamed/current problem is not a substitute for transfer.
            return {'kind':'gap','reason':'The weak concept has no different-domain representative exercise yet.','concepts':sorted(weak)}
        applied_tags={c for c,s in states.items() if s['correct_attempts']>0 and not s['transfer_demonstrated']}
        transfers=[p for p in candidates if p['transfer_from'] and applied_tags & set(p['mastery_tags']) and
                   any(e['problem_id']==p['transfer_from'] and e['domain']!=p['domain'] and stamp(now)-stamp(e['at'])>=timedelta(days=1) for e in successful)]
        if transfers:
            p=min(transfers,key=lambda p:(p['difficulty']['level'],p['problem_id']))
            return {'kind':'problem','problem_id':p['problem_id'],'reason':'Apply a known principle in a different business context.'}
        def priority(p):
            attempts=[e for e in tested if e['problem_id']==p['problem_id']]
            tested_at=max((e['at'] for e in attempts),default='')
            unseen=sum(states[tag]['mastery_state']=='UNSEEN' for tag in p['mastery_tags'])
            unmet=sum(states[t]['gaps']['application'] for t in p['evaluation_rules'].get('prerequisites',[]))
            return (bool(attempts),unmet,abs(int(p['difficulty']['level'][1])-target),tested_at,-unseen,p['problem_id'])
        p=min(candidates,key=priority)
        return {'kind':'problem','problem_id':p['problem_id'],'reason':'Build coverage at an appropriate difficulty; prefer less-tested concepts.','target_level':f'L{target}'}
