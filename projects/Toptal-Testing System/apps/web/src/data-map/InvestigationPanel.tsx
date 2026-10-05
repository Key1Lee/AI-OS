import {useEffect,useRef,useState} from 'react';
import {request} from '../api';
import {Badge} from '../components';
import type {Answer,Investigation,MapNode} from './types';

const empty:Answer={observed_failure:'',suspected_origin:'',grain:'',affected_outputs:[],fix_proposal:'',verification_plan:'',notes:''};

function browserDraft(key:string,session:Investigation):{draft:Answer;conflict:Answer|null}{
 // A tab owns its unsynced copy; shared storage lets another tab erase it.
 const saved={...empty,...session.draft};
 try{const stored=JSON.parse(sessionStorage.getItem(key)||'null');if(!stored)return {draft:saved,conflict:null};
  const copy={...saved,...stored.draft};
  if(stored.revision!==session.revision&&JSON.stringify(copy)!==JSON.stringify(saved))return {draft:saved,conflict:copy};
  return {draft:copy,conflict:null};
 }catch{return {draft:saved,conflict:null};}
}

export function InvestigationPanel({session,nodes,onUpdate,onError}:{session:Investigation;nodes:MapNode[];onUpdate:(s:Investigation)=>void;onError:(error:string)=>void}){
 const key='dm-draft-'+session.id;
 const [initial]=useState(()=>browserDraft(key,session));
 const [draft,setDraft]=useState<Answer>(initial.draft),[browserCopy,setBrowserCopy]=useState<Answer|null>(initial.conflict);
 const [hypothesis,setHypothesis]=useState(()=>sessionStorage.getItem(key+'-hypothesis')||'');const [busy,setBusy]=useState(false);const [saved,setSaved]=useState('');const requestId=useRef<string|null>(null);const submittedBody=useRef('');
 useEffect(()=>{sessionStorage.setItem(key+'-hypothesis',hypothesis);},[hypothesis,key]);
 useEffect(()=>{if(!browserCopy)sessionStorage.setItem(key,JSON.stringify({draft,revision:session.revision}));},[draft,key,session.revision,browserCopy]);
 useEffect(()=>{setSaved('Browser copy retained');},[draft,key]);
 const change=(field:keyof Answer,value:Answer[keyof Answer])=>setDraft(d=>({...d,[field]:value}));
 async function save(){setBusy(true);try{const value=await request<Investigation>('/map/investigations/'+session.id+'/draft','PUT',{...draft,revision:session.revision});onUpdate(value);setSaved('Saved to this profile');}catch(e){onError((e as Error).message);}finally{setBusy(false);}}
 async function submit(){setBusy(true);try{const body=JSON.stringify(draft);if(body!==submittedBody.current||!requestId.current){await request<Investigation>('/map/investigations/'+session.id+'/draft','PUT',{...draft,revision:session.revision}).then(onUpdate);requestId.current=crypto.randomUUID();submittedBody.current=body;}const value=await request<Investigation>('/map/investigations/'+session.id+'/submit','POST',{...draft,request_id:requestId.current});onUpdate(value);sessionStorage.removeItem(key);}catch(e){onError((e as Error).message);}finally{setBusy(false);}}
 const sorted=[...nodes].sort((a,b)=>a.name.localeCompare(b.name));
 const outputs=sorted.filter(n=>['output','metric'].includes(n.node_type));
 const nodeName=(id:string)=>sorted.find(n=>n.id===id)?.name||id;
 return <section className="panel dm-investigation" aria-label="Investigation notebook"><div className="dm-detail-heading"><div><div className="eyebrow">INVESTIGATION NOTEBOOK</div><h2>{session.mode==='assessment'?'Record your diagnosis':'Explore, record, then review'}</h2></div><Badge>{session.mode}</Badge></div><p>{session.scenario.brief}</p><p className="fine">{session.independent?'First assessment without recorded prior exposure.':'Learning or repeated exposure: this session cannot earn independent credit.'}</p>
 {session.result?<><div className="dm-score"><strong>{session.result.score} / {session.result.total}</strong><span>Observable investigation checks</span></div>{session.result.checks.map((c,i)=><div className="dm-check" key={i}><span>{c.satisfied?'✓':'○'}</span>{c.label}</div>)}<p>{session.result.feedback}</p><p className="fine">Unassessed: {session.result.unassessed.join(', ')}.</p><details><summary>Saved diagnosis</summary><dl className="dm-properties"><div><dt>Observed failure</dt><dd>{nodeName(session.result.answer.observed_failure)}</dd></div><div><dt>Candidate suspicion</dt><dd>{nodeName(session.result.answer.suspected_origin)}</dd></div></dl><h3>Proposed fix</h3><p>{session.result.answer.fix_proposal||'None recorded.'}</p><h3>Verification plan</h3><p>{session.result.answer.verification_plan||'None recorded.'}</p><h3>Evidence notes</h3><p>{session.result.answer.notes||'None recorded.'}</p></details></>:session.status!=='active'?<><p>This investigation is {session.status}. Its saved notes and actions remain available.</p><pre className="dm-code">{session.draft.notes||session.draft.fix_proposal||'No diagnosis draft was saved.'}</pre></>:<>
 {browserCopy&&<div className="notice">A newer diagnosis draft is saved. Your earlier browser copy is retained.<button onClick={()=>{setDraft(browserCopy);setBrowserCopy(null);}}>Restore browser notes</button></div>}
 <label className="dm-field">Working hypothesis<textarea value={hypothesis} onChange={e=>setHypothesis(e.target.value)} placeholder="State a hypothesis and the evidence that would test it." rows={3}/></label><button disabled={busy||!hypothesis.trim()} onClick={()=>void (async()=>{setBusy(true);try{onUpdate(await request('/map/investigations/'+session.id+'/hypotheses','POST',{text:hypothesis}));setHypothesis('');}catch(e){onError((e as Error).message);}finally{setBusy(false);}})()}>Record hypothesis</button>
 <div className="dm-form-grid"><label className="dm-field">Observed failure<select value={draft.observed_failure} onChange={e=>change('observed_failure',e.target.value)}><option value="">Choose a node</option>{sorted.map(n=><option key={n.id} value={n.id}>{n.name}</option>)}</select></label><label className="dm-field">Suspected origin<select value={draft.suspected_origin} onChange={e=>change('suspected_origin',e.target.value)}><option value="">Choose a node</option>{sorted.map(n=><option key={n.id} value={n.id}>{n.name}</option>)}</select></label></div>
 <label className="dm-field">Expected fact grain<select value={draft.grain} onChange={e=>change('grain',e.target.value)}><option value="">Choose a grain</option><option value="one_row_per_order">One row per order</option><option value="one_row_per_item">One row per item</option><option value="unknown">Unknown from the available evidence</option></select></label>
 <fieldset className="dm-output-options"><legend>Affected business outputs</legend>{outputs.map(n=><label key={n.id}><input type="checkbox" checked={draft.affected_outputs.includes(n.id)} onChange={e=>change('affected_outputs',e.target.checked?[...draft.affected_outputs,n.id]:draft.affected_outputs.filter(id=>id!==n.id))}/>{n.name}</label>)}</fieldset>
 <label className="dm-field">Proposed fix<textarea value={draft.fix_proposal} onChange={e=>change('fix_proposal',e.target.value)} rows={3}/></label><label className="dm-field">Verification plan<textarea value={draft.verification_plan} onChange={e=>change('verification_plan',e.target.value)} rows={3}/></label><label className="dm-field">Evidence notes<textarea value={draft.notes} onChange={e=>change('notes',e.target.value)} rows={3}/></label>
 <div className="dm-notebook-actions"><button onClick={()=>void save()} disabled={busy}>Save diagnosis draft</button><button className="primary" onClick={()=>void submit()} disabled={busy||!draft.observed_failure||!draft.suspected_origin}>Submit investigation</button></div><div className="fine" role="status">{saved}</div></>}
 <details className="dm-telemetry"><summary>Investigation history · {session.actions.length} actions</summary><p className="fine">Recorded tests inspected: {session.telemetry.recorded_tests_inspected}. Tests executed: 0. A verification plan has not been executed.</p>{session.actions.map(a=><div key={a.sequence} className="dm-action"><span>{a.kind.replaceAll('_',' ')}</span><span>{nodes.find(n=>n.id===a.target)?.name||(a.kind==='hypothesis'?String(a.payload.text||''):a.target||'')}</span></div>)}</details>
 </section>;
}
