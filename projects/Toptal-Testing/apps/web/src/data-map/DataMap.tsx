import {useEffect,useState} from 'react';
import {DataMap as MapView,Badge,DateText} from '@data-observability/ui';
import type {MapNode,MapSystem} from '@data-observability/ui';
import {initialize,request,mapClient} from '../api';
import {InvestigationPanel} from './InvestigationPanel';
import type {Investigation,HistoryRow} from './types';
import './training-map.css';

export function DataMap({standalone=false}:{standalone?:boolean}){
 const [session,setSession]=useState<Investigation|null>(null),[activeSession,setActiveSession]=useState<Investigation|null>(null),[history,setHistory]=useState<HistoryRow[]>([]);
 const [systemId,setSystemId]=useState('commerce-demo'),[ready,setReady]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false),[refreshKey,setRefreshKey]=useState(0);
 const assessment=activeSession?.mode==='assessment';
 useEffect(()=>{let alive=true;(async()=>{try{await initialize();const [available,active,records]=await Promise.all([request<MapSystem[]>('/map/systems'),request<Investigation|null>('/map/investigations/current'),request<HistoryRow[]>('/map/investigations/history')]);if(!alive)return;setHistory(records);let shown=active;const remembered=localStorage.getItem('dm-last-investigation');if(!shown&&remembered&&records.some(s=>s.id===remembered))shown=await request<Investigation>('/map/investigations/'+remembered);if(!alive)return;setSession(shown);setActiveSession(active);setSystemId(active?.system_id||(available.some(s=>s.id==='commerce-demo')?'commerce-demo':available[0]?.id)||'commerce-demo');setReady(true);}catch(e){if(alive){setError((e as Error).message);setReady(true);}}})();return()=>{alive=false;};},[]);
 async function work(action:()=>Promise<void>){if(busy)return;setBusy(true);setError('');try{await action();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function update(value:Investigation){setSession(value);setActiveSession(value.status==='active'?value:null);localStorage.setItem('dm-last-investigation',value.id);setHistory(await request('/map/investigations/history'));}
 async function syncActions(){const [value,records]=await Promise.all([request<Investigation|null>('/map/investigations/current'),request<HistoryRow[]>('/map/investigations/history')]);setActiveSession(value);setHistory(records);if(value){setSession(value);localStorage.setItem('dm-last-investigation',value.id);}}
 async function retainActiveDraft(){if(!activeSession)return;const retained=sessionStorage.getItem('dm-draft-'+activeSession.id);if(retained){const copy=JSON.parse(retained);await request('/map/investigations/'+activeSession.id+'/draft','PUT',{...copy.draft,revision:copy.revision});}}
 const start=(mode:'learning'|'assessment')=>void work(async()=>{if(activeSession&&(activeSession.mode!==mode||activeSession.system_id!==systemId))await retainActiveDraft();const value=await request<Investigation>('/map/investigations','POST',{system_id:systemId,mode});await update(value);setRefreshKey(n=>n+1);});
 const end=(learn:boolean)=>void work(async()=>{if(!activeSession)return;await retainActiveDraft();const value=await request<Investigation>('/map/investigations/'+activeSession.id+'/end','POST',{learn});setSession(learn?value:null);setActiveSession(learn?value:null);localStorage.removeItem('dm-last-investigation');await syncActions();setRefreshKey(n=>n+1);});
 const sidebar=(id:string,nodes:MapNode[])=><>
 {session&&session.system_id===id&&id==='commerce-demo'&&<InvestigationPanel key={session.id} session={session} nodes={nodes} onUpdate={s=>void update(s)} onError={setError}/>}
 <section className="panel dm-history"><h3>Saved investigations</h3>{history.length?history.slice(0,8).map(h=><button key={h.id} onClick={()=>void work(async()=>{const value=await request<Investigation>('/map/investigations/'+h.id);setSession(value);localStorage.setItem('dm-last-investigation',value.id);})}><span>{h.mode} · {h.status}</span><DateText value={h.started_at}/>{h.result&&<span>{h.result.score}/{h.result.total} checks</span>}</button>):<p>No investigations recorded.</p>}</section></>;
 return <>{error&&<div className="notice error" role="alert"><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss map error">×</button></div>}{!ready?<section className="panel loading">Loading metadata and saved investigations…</section>:<MapView client={mapClient} standalone={standalone} homeLabel="← Analytics Workbench" initialSystemId={systemId} refreshKey={refreshKey} extension={{
 busy,lockedSystem:assessment,allowExplanations:!assessment,showDiagnostics:!assessment&&activeSession?.mode==='learning',
 onAction:syncActions,onSystemChange:id=>{if(id!==systemId)setSession(null);setSystemId(id);},sidebar,
 badges:activeSession?.status==='active'&&<Badge tone={assessment?'amber':'green'}>{assessment?'Assessment · hints hidden':'Learning'}</Badge>,
 controls:(id,loading)=><div className="dm-mode-buttons"><button onClick={()=>start('learning')} disabled={loading||assessment}>Start Learning</button><button onClick={()=>start('assessment')} disabled={loading||id!=='commerce-demo'}>Start Assessment</button></div>,
 notice:assessment?<div className="dm-mode-note"><strong>Investigate independently.</strong><span>Failure evidence is visible. Select nodes to gather more; guided causes and hints stay hidden.</span><button onClick={()=>end(true)} disabled={busy}>End assessment and learn</button></div>:<div className="dm-mode-note"><span>{activeSession?.status==='active'?'Learning explanations may reveal the sample diagnosis.':'Choose Assessment before exploring for a first independent attempt. Opening details creates a learning record.'}</span>{activeSession?.status==='active'&&<button onClick={()=>end(false)} disabled={busy}>Finish learning</button>}</div>,
 incidentNotice:assessment&&<p className="fine">No automatic origin designation is supplied. The recorded evidence is available through node inspection.</p>
 }}/>}</>;
}
