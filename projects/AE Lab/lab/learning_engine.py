"""Requirements-first learning, safe disclosure and adaptive local evidence.

SQL executes in the consumer warehouse. Modeling/Quality/Observability and exact
recall checks call native siblings. Unstructured architecture and causal prose
require tutor review; they are never graded by matching keywords.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4
from .adapters.bridge import invoke, AdapterError
from .curriculum import POLICY
from .mastery import Mastery, stamp
from .problems import PROBLEM_MAP, PROBLEMS, VERSION, learner_problem
from .sql_lab.catalog import CATALOG as SQL
from .sql_lab.datasets import DOMAINS, fixture, T2
from .sql_lab.contracts import fingerprint
from .sql_lab.evaluator import evaluate, rowset, ERROR_CLASSES
from .sql_lab.integrations import native_type
from .sql_lab.oracles import latest
from .sql_lab.postgres import Postgres
from .store import StateError
from . import business_reasoning as reasoning
from .reasoning_fixtures import fixture as reasoning_fixture,VARIANTS

EMPTY={'columns':{'orderId':'VARCHAR','customerId':'VARCHAR','status':'VARCHAR','totalPriceCents':'BIGINT','currency':'VARCHAR','createdAt':'VARCHAR','updatedAt':'VARCHAR','sourceVersion':'INTEGER'},'rows':[]}
ORIGINAL_JOINS={'FIN-001':{'loans:payment_events':'1:M'},
 'EC-001':{'orders:order_items':'1:M','orders:refund_events':'1:M','order_items:refund_events':'M:M'},
 'SAAS-003':{'invoices:invoice_events':'1:M'}}


def concise(error,fix,why):
    return {'error':error,'fix':fix,'why':why,'try_again':'Correct this point, then submit again.'}


def nonempty(value,field,limit=4000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise StateError(f'{field}: enter a short non-empty response (at most {limit} characters).')
    return value.strip()


def keylist(value,field):
    if not isinstance(value,list) or not value or len(value)>4 or any(not isinstance(k,str) or not k for k in value) or len(set(value))!=len(value):
        raise StateError(f'{field}: declare one to four distinct column names.')
    return value

class LearningEngine:
    def __init__(self,store,postgres=None,clock=None):
        self.store=store;self.mastery=Mastery(store)
        self.postgres=postgres or Postgres()
        self.clock=clock or (lambda:datetime.now(timezone.utc))

    def now(self):return self.clock().isoformat()

    @staticmethod
    def join_rules(p,r):
        return p['evaluation_rules'].get('joins',ORIGINAL_JOINS.get(p['evaluation_rules'].get('sql_challenge_id'),{}) if r.get('reasoning_version')==2 else {})

    def problem(self,record):
        if record.get('kind')!=VERSION:raise StateError('Choose a curriculum learning session')
        p=PROBLEM_MAP[record['problem_id']]
        if record['definition_sha256']!=fingerprint(p):
            raise StateError('This problem definition changed. Keep the old evidence and start a new session.')
        return p

    def save(self,record):
        self.store.save(record)
        directory=self.store.root/record['run_id'];directory.mkdir(exist_ok=True)
        temp=directory/'learning-evidence.tmp'
        temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(directory/'learning-evidence.json')

    def start(self,problem_id,mode='LEARN'):
        if not isinstance(problem_id,str) or problem_id not in PROBLEM_MAP:raise StateError('Unknown learning problem')
        p=PROBLEM_MAP[problem_id]
        if not isinstance(mode,str) or mode not in p['modes']:raise StateError('This problem does not support the selected mode')
        r={'kind':VERSION,'run_id':str(uuid4()),'scenario_id':problem_id,'problem_id':problem_id,'mode':mode,
           'definition_sha256':fingerprint(p),'created_at':self.now(),'state':'READY','learning_step':0,
           'answers':{},'attempts':[],'hints':[],'revealed':False,'recall':False,'phases':{},'verification':None,
           'reviews':[],'assistance':{'automated_demo':False,'exposure':'Unassisted until hints or solution exposure'},'failure_diagnosis':None}
        r['reasoning_version']=2
        if p['kind']=='reasoning':
            prior=sum(s.get('problem_id')==problem_id for s in self.store.records())
            r.update(fixture_variant=VARIANTS[prior%len(VARIANTS)],clarifications=[])
        if p['kind']=='debug' and (mode in ('DEBUG','REVIEW') or p['problem_id']=='DEBUG-ORDER-001') and mode!='INCIDENT':
            c=SQL[p['evaluation_rules']['sql_challenge_id']]
            r['broken_output']=self.postgres.execute(p['artifacts']['broken_sql'],c,fixture(p['domain'],'clean'))
        self.save(r)
        for tag in p['mastery_tags']:self.mastery.add(tag,'introduced',p,r['created_at'],reference=r['run_id'])
        return r

    def view(self,record):
        p=self.problem(record)
        result={k:deepcopy(record[k]) for k in ('run_id','problem_id','scenario_id','mode','created_at','state','learning_step','hints','revealed','recall')}
        if record['recall']:
            result.update(problem={'problem_id':p['problem_id'],'title':'Quick recall','domain':p['domain']},
                          prompts=[q['prompt'] for q in record['recall_questions']],feedback=deepcopy(record.get('recall_feedback')))
            return result
        result['problem']=learner_problem(p,record['mode'])
        if p['kind']=='reasoning':
            data=reasoning_fixture(p['domain'],record['fixture_variant'])
            result['problem']['sample_rows']={t['name']:deepcopy(data[t['name']]) for t in p['tables']}
            result['fixture_variant']=record['fixture_variant']
            result['clarifications']=deepcopy(record.get('clarifications',[]))
            if record['learning_step']>=1:result['problem']['artifacts']['workbook']=reasoning.workbook(p)
        if p['kind'] in ('sql','debug'):result['problem']['artifacts']['join_pairs']=list(self.join_rules(p,record))
        result['prepared']=deepcopy(record['answers'])
        result['attempt_count']=len(record['attempts'])
        result['loop']=POLICY['loop']
        result['hint_limit']=POLICY['modes'][record['mode']]['hints']
        if record.get('broken_output') and record['mode']!='INCIDENT':result['broken_output']=deepcopy(record['broken_output'])
        if record['attempts']:
            attempt=record['attempts'][-1]
            result['submission']=deepcopy(attempt['answer'])
            result['feedback']=deepcopy(attempt['feedback'])
            result['status']=attempt['status']
            result['rubric']=deepcopy(attempt['evaluation'].get('rubric',{}))
            if attempt['status']=='FAIL':
                tags=p['mastery_tags']
                if any(t.startswith(('sql.joins','sql.grain','modeling.grain')) for t in tags):
                    result['related_practice']={'problem_id':'MODEL-GRAIN-001','reason':'A modeling row-meaning scenario can help explain incompatible measure and join grains.'}
            result['error_classes']=deepcopy(attempt['evaluation'].get('error_classes',[]))
            if 'query_plan' in attempt['evaluation']:result['query_plan']=deepcopy(attempt['evaluation']['query_plan'])
            if record['state']=='COMPLETED' and p['artifacts'].get('next_stage'):result['next_stage']=p['artifacts']['next_stage']
            result['followups']=p['followups'][:1]
            if p['kind']=='reasoning':
                e=attempt['evaluation']
                result['can_probe']=e.get('objective_status')=='PASS' and e['variant']==record['fixture_variant'] and record['fixture_variant']!=VARIANTS[-1]
                if record['mode']!='INTERVIEW' or record['state']=='COMPLETED':
                    reviewed=next((review for review in reversed(record['reviews']) if review['attempt_id']==attempt['attempt_id']),None)
                    if reviewed:result['judgment_review']=deepcopy(reviewed)
                    failures=[c for c in e['checks'] if not c['passed']]
                    data=reasoning_fixture(p['domain'],e['variant'])
                    result['reasoning_evidence']={'variant':e['variant'],'policy':e['policy'],'checks':deepcopy(failures[:1] or e['checks']),
                      'passed':sum(c['passed'] for c in e['checks']),'total':len(e['checks']),
                      'source_tables':{t['name']:data[t['name']] for t in p['tables']},'scope':e['scope'],
                      'join_trace':reasoning.join_trace(p,data)}
            if 'cases' in attempt['evaluation'] and (record['mode']!='INTERVIEW' or record['state']=='COMPLETED'):
                e=attempt['evaluation'];case=e['cases'][e['selected_case']]
                result['comparison']={k:deepcopy(case[k]) for k in ('source_tables','actual','expected','error','matches')}
                result['comparison']['diff']={k:case.get(k,[]) for k in ('missing_rows','unexpected_rows')}
                result['row_trace']=deepcopy(e['row_trace'])
                result['clauses']=deepcopy(e['issues'])
                result['join_evidence']=deepcopy(e['native'].get('modeling',{}).get('joins',[]))
                result['source_warnings']=[{'dataset':name,'failed_rows':test['failed_rows'],
                    'message':test['evidence']['message'],'severity':test['severity']}
                    for name,bundle in e['native'].get('quality',{}).get('bundles',{}).items() if name!='candidate'
                    for test in bundle['results'] if test['severity']=='WARNING' and test['status']!='PASS']
                result['test_summary']={'passed':sum(c['matches'] for c in e['cases']),'total':len(e['cases'])}
        if record['revealed']:result['solution']=p['solution']
        if record['mode']=='INTERVIEW' and record['state']!='COMPLETED':
            for field in ('rubric','error_classes','related_practice','query_plan'):result.pop(field,None)
            if record['attempts']:
                result['feedback']={'error':None if record['attempts'][-1]['status']=='PASS' else 'The answer needs further assessment or revision.',
                                    'fix':None,'why':'Defend your approach and name any remaining uncertainty.',
                                    'try_again':'You may revise or finish this interview question.'}
        result['assessment_scope']='Visible source facts are checked separately from evidence-backed tutor judgment; mastery requires transfer and spaced recall.' if p['kind']=='reasoning' else 'Objective SQL/model results are checked. Causal prose and architecture judgment require tutor review; no percentage mastery.'
        return result

    def catalog(self,mode='LEARN',focus='all'):
        if mode not in POLICY['modes']:raise StateError('Unknown learning mode')
        if focus not in ('all','sql','reasoning'):raise StateError('Unknown curriculum focus')
        items=[]
        for p in PROBLEMS:
            if mode not in p['modes']:continue
            if focus=='reasoning' and p['kind']!='reasoning':continue
            if focus=='sql' and p['kind'] not in ('sql','debug'):continue
            row={'problem_id':p['problem_id'],'title':p['neutral_title'] if POLICY['modes'][mode]['hide_skills'] else p['title'],
                 'domain':p['domain'],'difficulty':p['difficulty']['level'],'kind':p['kind']}
            if not POLICY['modes'][mode]['hide_skills']:row['skills_tested']=[t for t in p['skills_tested'] if t!='sql.joins.fanout']
            items.append(row)
        return items

    def recommend(self,mode='LEARN',focus='all'):
        if mode not in POLICY['modes']:raise StateError('Unknown learning mode')
        if focus not in ('all','sql','reasoning'):raise StateError('Unknown curriculum focus')
        candidates=[p for p in PROBLEMS if focus=='all' or focus=='reasoning' and p['kind']=='reasoning' or focus=='sql' and p['kind'] in ('sql','debug')]
        result=self.mastery.select(candidates,self.now(),mode,initial_level=3 if focus=='reasoning' else 2)
        if POLICY['modes'][mode]['hide_skills']:
            result.pop('concept',None)
            result.pop('concepts',None)
        return result

    def record_attempt(self,r,p,answer,evaluation):
        status=evaluation['status']
        attempt={'attempt_id':str(uuid4()),'at':self.now(),'answer':deepcopy(answer),'status':status,'evaluation':evaluation,
                 'assisted':bool(r['hints'] or r['revealed'] or r.get('reasoning_feedback_exposed')),'feedback':self.feedback(evaluation)}
        if p['kind']=='reasoning':attempt.update(context=deepcopy(r['answers']),question_snapshot=deepcopy(r.get('clarifications',[])))
        if p['kind']=='reasoning' and status=='FAIL' and r['mode']!='INTERVIEW':r['reasoning_feedback_exposed']=True
        r['attempts'].append(attempt);r['state']='REVIEW_PENDING' if status=='REVIEW_REQUIRED' else 'VERIFIED' if status=='PASS' else 'RETRY'
        r['learning_step']=3 if status=='PASS' else 2
        self.save(r)
        # Unavailable adapters and pending review are not evidence of learner failure.
        if status not in ('BLOCKED','REVIEW_REQUIRED'):
            for tag in p['mastery_tags']:
                if status=='FAIL' and tag=='sql.grain.output_keys' and evaluation.get('rubric',{}).get('grain_correctness')=='PASS':continue
                self.mastery.add(tag,'attempt',p,attempt['at'],passed=status=='PASS',assisted=attempt['assisted'],reference=attempt['attempt_id'],error_classes=evaluation.get('error_classes'))
                if status=='PASS' and tag not in evaluation.get('unexercised_techniques',[]):self.mastery.add(tag,'applied',p,attempt['at'],passed=True,assisted=attempt['assisted'],reference=attempt['attempt_id'])
        return r

    @staticmethod
    def feedback(e):
        if e.get('business_feedback'):return deepcopy(e['business_feedback'])
        if e['status']=='PASS':return {'error':None,'fix':None,'why':'The submitted output satisfies the objective checks. Explain the causal reasoning to your tutor.','try_again':'Answer the follow-up, then connect the principle.'}
        if e['status']=='REVIEW_REQUIRED':return concise('Objective checks passed; reasoning awaits tutor review.' if e.get('objective_status')=='PASS' else 'Design saved; judgment awaits tutor review.','Defend the business definition, grain and tradeoffs against the follow-up.','Free text cannot be certified by keyword matching.')
        if e['status']=='BLOCKED':return concise('Technical validation is unavailable.','Restore the named adapter and resubmit; your answer is saved.','Missing evidence is not a learner failure.')
        if e.get('grain_declared_correctly') is False:
            return concise('The declared input or output key does not match its row meaning.',
                           'Return to requirements and correct the grain declaration.',
                           'Matching a few output numbers does not establish the declared grain.')
        if e.get('cases'):
            case=e['cases'][e['selected_case']]
            if case['error']:
                return concise(case['error']['message'][:400],'Correct the indicated SQL clause or execution error.','The query did not produce a verifiable rowset.')
            if not case.get('columns_match',False):
                return concise('Output columns differ from the requested contract.','Use the required output column names.','The consumer needs a stable output schema.')
            issues=e.get('issues',[])
            risk=next((i for i in issues if i['code'] not in ('fixture_mismatch','execution_failure')),None)
            if risk:return concise('The returned rows differ from the business requirement.',risk['explanation'], 'The displayed failing fixture makes this assumption observable.')
            return concise('The returned keys or values differ from the expected result.','Trace one differing row from source to output.','A runnable query can still change row meaning or omit an entity.')
        return concise(e.get('first_failure','The model declaration differs from the producer contract.'),
                       'Correct that declaration before changing the remaining fields.','Keys must support the stated row meaning, including historical versions.')

    def model_evaluate(self,p,answer):
        rules=p['evaluation_rules']['expected']
        for f in ('input_grain','output_grain'):nonempty(answer.get(f),f,100)
        for f in ('input_key','output_key'):keylist(answer.get(f),f)
        results=[]
        for variant,seed in (('clean',1),('adversarial',1),('recall',3)):
            data=fixture(p['domain'],variant,seed);source=p['tables'][0]['name'];t=DOMAINS[p['domain']].table(source)
            if p['domain']=='fintech':
                output=latest(data[source],'transaction_id');out_grain='logical payment transaction';out_pk=['transaction_id']
            else:
                # Authored as-of fixture projection; engine owns grain/key assertions.
                output=[v for v in data[source] if v['version_id'] in ('V2','V3','V5')];out_grain='subscription at reporting instant';out_pk=['subscription_id']
            def transported(name,records,grain,pk):
                return {'columns':{k:native_type(v) for k,v in t.columns.items()},'rows':[[r[k] for k in t.columns] for r in records],
                        'grain':grain,'grain_label':grain,'primary_key':pk,'label':name,'description':p['business_context']}
            tables={'raw_orders':EMPTY,source:transported(source,data[source],t.entity,list(t.primary_key)),
                    'resolved':transported('resolved',output,out_grain,out_pk)}
            declared=invoke('modeling',{'tables':tables,'declarations':[
                {'table':source,'grain':answer['input_grain'],'primary_key':answer['input_key']},
                {'table':'resolved','grain':answer['output_grain'],'primary_key':answer['output_key']}]},worker='learning_modeling.py')
            results.append(declared)
        extras={k:answer.get(k) in allowed for k,allowed in rules.items() if k not in ('input_grain','input_key','output_grain','output_key')}
        passed=all(r['status']=='PASS' for r in results) and all(extras.values())
        first=next((test['name'] for r in results for d in r['declarations'] for test in d['tests'] if test['status']=='fail'),None)
        first=first or next((k for k,v in extras.items() if not v),None)
        return {'status':'PASS' if passed else 'FAIL','native_modeling':results,'policy_checks':extras,
                'first_failure':f'{first} does not match the row contract.' if first else None,
                'scope':'Native grain/keys plus authored exact interval and snapshot-policy choices. Causal prose unassessed.'}

    def action(self,record,action,answer=None):
        r=deepcopy(record);p=self.problem(r);answer=answer or {}
        if not isinstance(answer,dict):raise StateError('Submit a structured answer object')
        if r['recall']:
            if action!='submit_recall':raise StateError('Answer the recall prompts')
            return self.submit_recall(r,answer)
        if action=='ask':
            if p['kind']!='reasoning' or r['state']=='COMPLETED':raise StateError('Ask clarification during an active business reasoning case')
            if len(r['clarifications'])>=12:raise StateError('Keep this case to twelve focused clarification questions')
            r['clarifications'].append({'question_id':str(uuid4()),'question':nonempty(answer.get('question'),'stakeholder question',1800),'status':'PENDING_TUTOR_REVIEW'})
            self.save(r);return r
        if action=='probe':
            if p['kind']!='reasoning' or not r['attempts'] or r['attempts'][-1]['evaluation'].get('objective_status')!='PASS' or r['attempts'][-1]['evaluation'].get('variant')!=r['fixture_variant']:raise StateError('Attempt and validate the current evidence before requesting a new evidence probe')
            index=VARIANTS.index(r['fixture_variant'])
            if index==len(VARIANTS)-1:raise StateError('All authored evidence variants have been shown')
            r.update(fixture_variant=VARIANTS[index+1],state='READY',learning_step=0,answers={})
            self.save(r);return r
        if action=='next_stage':
            next_id=p['artifacts'].get('next_stage')
            if r['state']!='COMPLETED' or not next_id:raise StateError('Finish the current stage before changing the requirement')
            return self.start(next_id,r['mode'] if r['mode'] in PROBLEM_MAP[next_id]['modes'] else 'LEARN')
        if r['state']=='COMPLETED' and action not in ('reveal',):raise StateError('This session is complete; start a different context or recall')
        step=r['learning_step']
        if action=='predict':
            if step!=0:raise StateError('Record your first observation at the problem step')
            if p['artifacts'].get('prediction_sql'):
                rows=answer.get('prediction_rows')
                if not isinstance(rows,list) or len(rows)>200 or any(not isinstance(x,dict) for x in rows):raise StateError('Predict the returned rows as a JSON array of objects')
                c=SQL[p['evaluation_rules']['sql_challenge_id']]
                actual=self.postgres.execute(p['artifacts']['prediction_sql'],c,fixture(c.domain,'clean'))
                r['answers']['output_prediction']={'rows':rows,'matches':rowset(rows,actual['columns'])==rowset(actual['rows'],actual['columns'])}
            r['answers']['prediction']=nonempty(answer.get('prediction'),'prediction',1200);r['learning_step']=1
            if p['kind']=='reasoning' and len(r['clarifications'])<12:
                r['clarifications'].append({'question_id':str(uuid4()),'question':r['answers']['prediction'],'status':'PENDING_TUTOR_REVIEW'})
        elif action=='prepare':
            if step!=1:raise StateError('Make an observation before declaring requirements')
            requirements=nonempty(answer.get('requirements'),'requirements',2500)
            proposal=nonempty(answer.get('proposal'),'proposal',1200)
            input_grain=nonempty(answer.get('input_grain'),'input grain',1200)
            output_grain=nonempty(answer.get('output_grain'),'output grain',1200)
            prepared={'requirements':requirements,'proposal':proposal,'input_grain':input_grain,'output_grain':output_grain}
            if p['kind'] in ('sql','debug'):
                inputs=answer.get('inputs')
                if not isinstance(inputs,dict) or set(inputs)!={t['name'] for t in p['tables']}:raise StateError('Declare a key for each displayed input table')
                prepared['inputs']={k:keylist(v,k) for k,v in inputs.items()};prepared['output_key']=keylist(answer.get('output_key'),'output key')
                rules=p['evaluation_rules']
                join_rules=self.join_rules(p,r)
                if join_rules:
                    joins=answer.get('joins')
                    if not isinstance(joins,dict) or set(joins)!=set(join_rules):raise StateError('Declare left/right grain, relationship and expected output grain for every listed join')
                    prepared['joins']={}
                    for pair,declaration in joins.items():
                        if not isinstance(declaration,dict) or declaration.get('relationship') not in ('1:1','1:M','M:1','M:M'):raise StateError('Join relationship must be 1:1 / 1:M / M:1 / M:M')
                        prepared['joins'][pair]={f:nonempty(declaration.get(f),f,1200) for f in ('left_grain','right_grain','relationship','output_grain')}
                if rules.get('window_reasoning'):
                    window=answer.get('window')
                    if not isinstance(window,dict):raise StateError('Declare the window partition, order and visible rows/frame')
                    prepared['window']={f:nonempty(window.get(f),f,1200) for f in ('partition','order','frame')}
                if p['artifacts'].get('duplicate_reasoning'):prepared['duplicate_identity']=nonempty(answer.get('duplicate_identity'),'logical duplicate identity',1200)
            r['answers']['preparation']=prepared;r['learning_step']=2
        elif action=='submit':
            if step!=2:raise StateError('Predict and declare requirements/grain before submitting')
            nonempty(answer.get('reason'),'reason',2500)
            try:
                if p['kind'] in ('sql','debug'):
                    c=SQL[p['evaluation_rules']['sql_challenge_id']];prepared=r['answers']['preparation']
                    if c.manual_criteria and (r['mode'] in ('REVIEW','PERFORMANCE','SYSTEM_DESIGN') or c.difficulty>=5):
                        nonempty(answer.get('assessment'),'business, clarity and performance assessment',6000)
                    query=nonempty(answer.get('sql'),'SQL',10000)
                    e=evaluate(c,query,{'inputs':prepared['inputs'],'output':prepared['output_key'],'reason':answer['reason']},
                               self.store.root/r['run_id'],r['run_id'],self.postgres)
                    if any(prepared['joins'][pair]['relationship']!=relationship for pair,relationship in self.join_rules(p,r).items()):
                        e['grain_declared_correctly']=False;e['status']='FAIL';e['error_classes']=['JOIN_ERROR','GRAIN_ERROR'];e['rubric']['grain_correctness']='FAIL'
                    if r['mode']=='PERFORMANCE' and e['status']=='PASS':
                        e['query_plan']=self.postgres.execute(query,c,fixture(c.domain),explain=True)
                    if c.manual_criteria and (r['mode'] in ('REVIEW','PERFORMANCE','SYSTEM_DESIGN') or c.difficulty>=5) and e['status']=='PASS':
                        e['objective_status']='PASS';e['status']='REVIEW_REQUIRED';e['criteria']=list(c.manual_criteria)
                elif p['kind']=='modeling':e=self.model_evaluate(p,answer)
                elif p['kind']=='reasoning':e=reasoning.evaluate(p,answer,r['fixture_variant'])
                else:
                    nonempty(answer.get('design'),'design',8000)
                    e={'status':'REVIEW_REQUIRED','criteria':p['evaluation_rules']['criteria'],'scope':'Tutor review required; no automatic prose certification.'}
            except (AdapterError, RuntimeError) as exc:e={'status':'BLOCKED','adapter_error':str(exc)}
            return self.record_attempt(r,p,answer,e)
        elif action=='revise':
            if step!=2:raise StateError('Revise requirements after preparing an answer')
            r['learning_step']=1
        elif action=='hint':
            maximum=POLICY['modes'][r['mode']]['hints']
            if len(r['hints'])>=maximum:raise StateError('No more hints in this mode')
            r['hints'].append(p['hints'][len(r['hints'])]);r['assistance']['exposure']='Hint-assisted; new answers cannot establish unassisted mastery'
        elif action=='reveal':
            if not r['attempts']:raise StateError('Attempt the problem before revealing a solution')
            if r['mode']=='INTERVIEW' and r['state']!='COMPLETED':raise StateError('Finish the interview question before reviewing the solution')
            failures=sum(a['status']=='FAIL' for a in r['attempts'])
            if failures<3 and answer.get('explicit_request') is not True:raise StateError('A solution requires three failed attempts or your explicit request')
            r['revealed']=True;r['assistance']['exposure']='Solution exposed; assisted evidence only'
        elif action=='finish':
            if not r['attempts']:raise StateError('Attempt the problem before completing this session')
            if p['kind']=='reasoning' and r['attempts'][-1]['evaluation'].get('variant')!=r['fixture_variant']:raise StateError('Attempt the current evidence before finishing')
            if r['mode']!='INTERVIEW' and r['attempts'][-1]['status']!='PASS':raise StateError('Verify an answer or obtain tutor review before completing')
            r['answers']['connection']=nonempty(answer.get('connection'),'connection',2000)
            r['state']='COMPLETED';r['learning_step']=9
            if p['kind']=='reasoning' and r['attempts'][-1]['status']=='FAIL':r['reasoning_feedback_exposed']=True
        else:raise StateError('Unknown learning action')
        self.save(r);return r

    def review(self,run_id,attempt_id,reviewer,rationale,criteria,concepts,error_classes=None,judgment=None):
        """Trusted tutor entrypoint; no learner-facing web route calls this."""
        r=self.store.get(run_id);p=self.problem(r)
        nonempty(reviewer,'reviewer',120);nonempty(rationale,'review rationale',3000)
        a=next((a for a in r['attempts'] if a['attempt_id']==attempt_id),None)
        if not a:raise StateError('Review needs a real saved attempt')
        if p['kind']=='reasoning':
            assessed=reasoning.review_judgment(p,a,judgment)
            if criteria!=assessed:raise StateError('Boolean criteria must agree with the evidence-backed semantic scores')
        if not isinstance(criteria,dict) or not criteria or any(type(v) is not bool for v in criteria.values()):raise StateError('Review criteria need explicit boolean results')
        if not isinstance(concepts,list) or not concepts or not set(concepts)<=set(p['mastery_tags']):raise StateError('Review only the concepts actually assessed in this problem')
        if any(review['attempt_id']==attempt_id for review in r['reviews']):raise StateError('This attempt already has a tutor review')
        if error_classes is not None and (not isinstance(error_classes,list) or not set(error_classes)<=set(ERROR_CLASSES)):raise StateError('Use the authored error classification names')
        manual=a['evaluation'].get('criteria',p['evaluation_rules']['criteria'])
        needs_review=p['kind']=='architecture' or a['status']=='REVIEW_REQUIRED'
        if needs_review and set(criteria)!=set(manual):raise StateError('Assess every authored review criterion explicitly')
        passed=all(criteria.values());at=self.now()
        review={'attempt_id':attempt_id,'reviewer':reviewer,'rationale':rationale,'criteria':criteria,'concepts':concepts,'at':at,'passed':passed}
        if p['kind']=='reasoning':review['judgment']=deepcopy(judgment)
        if error_classes:
            review['error_classes']=error_classes;a['evaluation']['error_classes']=sorted(set(a['evaluation'].get('error_classes',[])+error_classes))
        r['reviews'].append(review)
        if needs_review:
            a['status']='PASS' if passed else 'FAIL';a['feedback']=self.feedback({'status':a['status'],'first_failure':next((k for k,v in criteria.items() if not v),None)})
            if p['kind']=='reasoning':
                a['evaluation']['rubric']['judgment']='PASS' if passed else 'FAIL'
                if passed:a['feedback']={'error':None,'fix':None,'why':'The source facts and evidence-backed reasoning meet the reviewed criteria.','try_again':p['followups'][0]}
                if not passed:
                    failed=next(k for k,v in criteria.items() if not v)
                    a['feedback']={'error':'Reasoning needs revision: '+failed.replace('_',' ')+'.','fix':judgment[failed]['rationale'],
                     'why':p['evaluation_rules']['rubric_guidance'][failed],'try_again':p['followups'][0]}
                    if r['mode']!='INTERVIEW' or r['state']=='COMPLETED':r['reasoning_feedback_exposed']=True
            completed=r['state']=='COMPLETED'
            current=a is r['attempts'][-1] and (p['kind']!='reasoning' or a['evaluation']['variant']==r['fixture_variant'])
            if current:
                r['state']='COMPLETED' if completed else 'VERIFIED' if passed else 'RETRY';r['learning_step']=9 if completed else 3 if passed else 2
            for tag in concepts if p['kind']=='reasoning' else p['mastery_tags']:
                self.mastery.add(tag,'attempt',p,at,passed=passed,assisted=a['assisted'],reference=attempt_id,reviewer=reviewer,note=rationale,error_classes=error_classes)
                if passed and tag not in a['evaluation'].get('unexercised_techniques',[]):self.mastery.add(tag,'applied',p,at,passed=True,assisted=a['assisted'],reference=attempt_id,reviewer=reviewer,note=rationale)
            for dimension,ok in criteria.items():
                if dimension in a['evaluation'].get('rubric',{}):a['evaluation']['rubric'][dimension]='PASS' if ok else 'FAIL'
        if passed:
            for tag in concepts:
                self.mastery.add(tag,'understood',p,at,passed=True,assisted=a['assisted'],reference=attempt_id,reviewer=reviewer,note=rationale)
                if (p['kind']=='debug' or p['kind']=='reasoning' and p['artifacts']['diagnosis_task']) and a['status']=='PASS' and tag not in a['evaluation'].get('unexercised_techniques',[]):
                    self.mastery.add(tag,'debugged',p,at,passed=True,assisted=a['assisted'],reference=attempt_id,reviewer=reviewer,note=rationale)
        self.save(r);return r

    def respond_to_question(self,run_id,question_id,reviewer,category,rationale,fact_id=None,response=None):
        """Trusted semantic tutor action, intentionally absent from public HTTP."""
        r=self.store.get(run_id);p=self.problem(r)
        if p['kind']!='reasoning':raise StateError('Choose a business reasoning case')
        nonempty(reviewer,'reviewer',120);nonempty(rationale,'clarification assessment rationale',3000)
        if category not in reasoning.CATEGORIES:raise StateError('Use one of the five clarification classifications')
        inquiry=next((q for q in r['clarifications'] if q['question_id']==question_id),None)
        if not inquiry or inquiry['status']!='PENDING_TUTOR_REVIEW':raise StateError('Assess one pending real learner question exactly once')
        if fact_id is not None:
            fact=next((f for f in p['evaluation_rules']['clarifications'] if f['id']==fact_id),None)
            if not fact or fact['category']!=category:raise StateError('The authored stakeholder fact must match its reviewed classification')
            response=fact['response']
        inquiry.update(status='ANSWERED',category=category,response=nonempty(response,'stakeholder response',6000),reviewer=reviewer,rationale=rationale,at=self.now())
        self.save(r);return r

    def start_recall(self,problem_id,concept=None):
        if not isinstance(problem_id,str) or problem_id not in PROBLEM_MAP:raise StateError('Unknown recall problem')
        p=PROBLEM_MAP[problem_id];questions=[q for q in p['recall'] if concept is None or concept in q['concepts']]
        if not questions:raise StateError('No recall question exists for this concept')
        for tag in {t for q in questions for t in q['concepts']}:
            s=self.mastery.state(tag)
            if not s['due_recall'] or stamp(self.now())<stamp(s['due_recall']):raise StateError('Practice first; spaced recall is not due yet')
        r={'kind':VERSION,'run_id':str(uuid4()),'problem_id':problem_id,'scenario_id':problem_id,'mode':'PRACTICE',
           'definition_sha256':fingerprint(p),'created_at':self.now(),'state':'READY','learning_step':7,
           'recall':True,'recall_questions':questions,'hints':[],'revealed':False,'attempts':[],
           'assistance':{'automated_demo':False},'answers':{},'phases':{},'verification':None,'reviews':[]}
        self.save(r);return r

    def submit_recall(self,r,answer):
        if r['state']=='COMPLETED':raise StateError('This recall session has already been assessed')
        p=self.problem(r);responses=answer.get('responses')
        if not isinstance(responses,list) or len(responses)!=len(r['recall_questions']):raise StateError('Answer each short recall question')
        fields={};allowed={};criteria=[]
        for i,(q,response) in enumerate(zip(r['recall_questions'],responses)):
            if isinstance(response,bool) or not isinstance(response,(str,int)):raise StateError('Recall answers must be short strings or integers')
            name=f'q{i}';fields[name]=str(response).strip().casefold();allowed[name]=[str(x).casefold() for x in q['accepted']];criteria.append([name,'Exact authored recall check'])
        evaluation=invoke('testing',{'stage':'recall','answer':fields,'authored':{
            'scenario_id':p['problem_id'],'concept':' / '.join(p['mastery_tags']),'prompt':'Short spaced recall',
            'criteria':criteria,'expected':allowed}})
        r['answers']={'responses':responses,'evaluation':evaluation};r['state']='COMPLETED';r['learning_step']=9
        r['recall_feedback']={'error':None if evaluation['outcome']=='pass' else 'One recall response needs another look.',
            'fix':None if evaluation['outcome']=='pass' else 'Revisit the principle in a different context.',
            'why':'Exact short recall checks; other valid phrasing can be reviewed by a tutor.','try_again':'A later spaced check will use a different context.'}
        self.save(r)
        checks={c['criterion_id']:c['passed'] for c in evaluation['checks'] if 'criterion_id' in c}
        # Native returned met/missing fields vary; authored exact outcomes are in objective check IDs.
        for i,q in enumerate(r['recall_questions']):
            name=f'q{i}'
            objective=next((c for c in evaluation['checks'] if c.get('id')==name or c.get('criterion_id')==name),None)
            passed=objective['passed'] if objective else evaluation['outcome']=='pass'
            for tag in q['concepts']:self.mastery.add(tag,'recall',p,self.now(),passed=passed,reference=r['run_id'])
        return r
