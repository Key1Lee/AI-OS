import {lazy,Suspense,useEffect,useState} from 'react';
import {initialize,request} from './api';
import {Dashboard} from './Dashboard';
import {Competencies,History,Library,Mistakes,Reviews,Roadmap} from './EvidenceViews';
import {Icon} from './components';
import type {Attempt,Dashboard as DashboardData,Exercise} from './types';

const nav=[['overview','Overview','overview'],['data-map','Data System Map','competencies'],['practice','Practice','practice'],['interview','SQL Interview','interview'],['competencies','Competency Map','competencies'],['mistakes','Mistake Review','mistakes'],['reviews','Review Queue','review'],['library','Exercise Library','library'],['history','Session History','history'],['roadmap','Labs & Take-Home','roadmap']];
const Solve=lazy(()=>import('./Solve').then(module=>({default:module.Solve})));
const DataMap=lazy(()=>import('./data-map/DataMap').then(module=>({default:module.DataMap})));

export function App(){
 const [view,setView]=useState('overview');const [data,setData]=useState<DashboardData|null>(null);const [exercises,setExercises]=useState<Exercise[]>([]);const [attempt,setAttempt]=useState<Attempt|null>(null);
 const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [theme,setTheme]=useState(()=>localStorage.getItem('ae-theme')||'dark');
 useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('ae-theme',theme);},[theme]);
 async function refresh(){const snapshot=await request<DashboardData>('/dashboard');setData(snapshot);return snapshot;}
 useEffect(()=>{let alive=true;(async()=>{try{await initialize();const [snapshot,bank]=await Promise.all([request<DashboardData>('/dashboard'),request<Exercise[]>('/exercises')]);if(!alive)return;setData(snapshot);setExercises(bank);const hash=window.location.hash.slice(1);if(hash.startsWith('attempt/')){const a=await request<Attempt>('/attempts/'+encodeURIComponent(hash.slice(8)));if(alive){setAttempt(a);setView('solve');}}else if(nav.some(n=>n[0]===hash))setView(hash);}catch(e){if(alive)setError((e as Error).message);}})();return ()=>{alive=false;};},[]);
 async function perform(work:()=>Promise<void>){if(busy)return;setBusy(true);setError('');try{await work();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 function navigate(page:string){setView(page);setAttempt(null);window.location.hash=page;setError('');void refresh().catch(e=>setError(e.message));}
 function open(a:Attempt){setAttempt(a);setView('solve');window.location.hash='attempt/'+a.id;window.scrollTo({top:0,behavior:'instant'});}
 const start=(payload:unknown={})=>void perform(async()=>{open(await request<Attempt>('/attempts','POST',payload));await refresh();});
 const load=(id:string)=>void perform(async()=>{open(await request<Attempt>('/attempts/'+id));});
 function update(a:Attempt){setAttempt(a);if(a.status==='completed')void refresh().catch(e=>setError(e.message));}
 const revise=()=>void perform(async()=>{open(await request<Attempt>('/attempts/'+attempt!.id+'/revise','POST'));await refresh();});
 return <div className="app-shell"><aside className="sidebar"><a className="brand" href="#overview" onClick={e=>{e.preventDefault();navigate('overview');}}><span className="brand-symbol">w<span>·</span></span><div>Workbench<small>ANALYTICS ENGINEERING</small></div></a><div className="workspace-label"><span className="workspace-dot"/>Personal workspace</div><div className="nav-label">TRAINING & EVIDENCE</div><nav aria-label="Main navigation">{nav.map(([id,label,icon])=><button key={id} className={view===id?'active':''} onClick={()=>navigate(id)} disabled={busy}><Icon name={icon}/><span>{label}</span>{id==='reviews'&&Boolean(data?.stats.due_reviews)&&<span className="nav-count">{data!.stats.due_reviews}</span>}{id==='roadmap'&&<span className="nav-planned">Planned</span>}</button>)}</nav><div className="sidebar-bottom"><div className="local-status"><span/>Local SQL training</div><p>Your work stays in this project.<br/>No API key needed for SQL.</p><button className="theme-button" onClick={()=>setTheme(theme==='dark'?'light':'dark')}>{theme==='dark'?'☼ Light':'☾ Dark'} appearance</button><div className="sidebar-version">Phase 1 + adaptive evidence · v0.1</div></div></aside><div className="main-shell"><header className="topbar"><span>{view==='solve'?'Training / '+(attempt?.exercise.domain||'SQL'):nav.find(n=>n[0]===view)?.[1]||'Overview'}</span><div><span className="topbar-note">Independent practice. Observable evidence.</span><span className="profile">You</span></div></header><main className={view==='solve'?'main-content solving':'main-content'} aria-busy={busy}>{error&&<div className="notice error" role="alert"><span>{error}</span><button aria-label="Dismiss message" onClick={()=>setError('')}>×</button></div>}{!data?<section className="panel loading"><h1>{error?'Unable to load training':'Opening your workspace…'}</h1><p>{error?'Keep the trainer terminal running and refresh this page.':'Loading your exercise bank and saved evidence.'}</p></section>:<>
 {view==='overview'&&<Dashboard data={data} onContinue={()=>start()} onNavigate={navigate} onAttempt={load}/>}
 {['practice','library','interview'].includes(view)&&<Library key={view} exercises={exercises} data={data} onStart={start} mode={view==='interview'?'interview':'practice'}/>}
 {view==='competencies'&&<Competencies data={data} onAttempt={load}/>}
 {view==='mistakes'&&<Mistakes data={data} onStart={()=>start()} onAttempt={load}/>}
 {view==='reviews'&&<Reviews data={data} onStart={start}/>}
 {view==='history'&&<History data={data} onAttempt={load}/>}
 {view==='roadmap'&&<Roadmap/>}
 {view==='data-map'&&<Suspense fallback={<section className="panel loading">Opening Data System Map…</section>}><DataMap/></Suspense>}
 {view==='solve'&&attempt&&<Suspense fallback={<section className="panel loading">Opening the SQL editor…</section>}><Solve key={attempt.id} attempt={attempt} data={data} theme={theme} onUpdate={update} onContinue={()=>start()} onRevise={revise} onBack={()=>navigate('overview')} onError={setError}/></Suspense>}
 </>}</main><footer className="main-footer">Original training content · Practice ratings are scoped to tested competencies · Independent preparation, not an official Toptal assessment</footer></div></div>;
}
