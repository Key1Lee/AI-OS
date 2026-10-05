import { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowRight, Check, ChevronRight, Code2, Database, FlaskConical, GitMerge, KeyRound, Layers3, Play, RotateCcw, ShieldCheck, Sigma, Table2, Workflow, X } from 'lucide-react';
import { api, download } from './api';
import { ModelQuestions, Proofs, SqlBlock, StatusPill, StepDetails, Table } from './components';
import { BuildLab, JoinLab, MetricLab } from './labs';
import { StoryFlow } from './StoryFlow';
import type { BuildRequest, BuildResult, GrainResult, Metric, Model, Scenario, StageResult, Step } from './types';

type View = 'story' | 'join' | 'build' | 'metric';
const navigation = [
  {id:'story' as View, label:'Transformation story', icon:Workflow, number:'01'},
  {id:'join' as View, label:'Join lab', icon:GitMerge, number:'02'},
  {id:'build' as View, label:'Build & verify', icon:ShieldCheck, number:'03'},
  {id:'metric' as View, label:'Semantic metric', icon:Sigma, number:'04'},
];

function GrainInspector({ model, busy, declare, stage, advanced, ready, onAdvanced }: {
  model:Model; busy:boolean; declare:(grain:string,key:string[])=>void; stage:()=>void;
  advanced:boolean; ready:boolean; onAdvanced:()=>void;
}) {
  const [grain, setGrain] = useState(model.grain.declared ?? '');
  const [key, setKey] = useState(model.primary_key.join(','));
  const draftChanged = model.grain.declared !== null && (grain !== model.grain.declared || key !== model.primary_key.join(','));
  const grains = [['source_order_version','One source order version'],['order','One order'],['order_item','One order item'],['customer','One customer'],['payment','One payment attempt'],['product','One product'],['return','One return']];
  return <aside className="card inspector" aria-label="Model inspector"><div className="inspector-head"><span className="eyebrow">MODEL INSPECTOR</span><span className="tag">{model.layer}</span></div><h3>{model.name}</h3><p className="inspector-description">{model.why}</p><ModelQuestions model={model}/>
    {model.layer === 'source' && <div className="grain-form"><h4>Start with one row.</h4><p>Declare its meaning and a key. We’ll check both against the producer contract and actual records.</p><label>What does one row represent?<select aria-label="Source grain" value={grain} onChange={e=>setGrain(e.target.value)}><option value="">Choose the row’s meaning…</option>{grains.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><label>Which key identifies that row?<select aria-label="Source primary key" value={key} onChange={e=>setKey(e.target.value)}><option value="">Choose a source key…</option>{model.columns.map(c=><option key={c.name} value={c.name}>{c.name}</option>)}{model.id==='raw_orders'&&<option value="orderId,sourceVersion">orderId + sourceVersion</option>}</select></label><button className="secondary-button" disabled={!grain || !key || busy} onClick={()=>declare(grain,key.split(','))}><KeyRound size={15}/>Check my grain</button>
      {model.tests.length > 0 && <Proofs tests={model.tests}/>}
      {draftChanged && <p className="draft-note">Selection changed. Check your new grain and key before staging.</p>}
      {model.id === 'raw_orders' && model.status === 'pass' && <button className="primary-button full-width" disabled={busy || draftChanged} onClick={stage}><Play size={16}/>{ready ? 'Run staging again' : 'Create staging model'}</button>}
    </div>}
    {model.layer !== 'source' && model.tests.length>0 && <details className="inspector-proof"><summary>Inspect model assertions <ChevronRight size={14}/></summary><Proofs tests={model.tests}/></details>}
    {advanced && <div className="contract-note"><Layers3 size={15}/><p><strong>Materialization: {model.materialization}</strong><br/>A local fixture choice. Production choices depend on build cost, query cost, storage, and freshness.</p></div>}
    {model.sql && (advanced ? <SqlBlock sql={model.sql}/> : <button className="text-button" onClick={onAdvanced}><Code2 size={15}/>Inspect SQL in Advanced mode</button>)}
  </aside>;
}

export default function App() {
  const [scenario, setScenario] = useState<Scenario|null>(null);
  const [view, setView] = useState<View>('story');
  const [advanced, setAdvanced] = useState(false);
  const [selected, setSelected] = useState('raw_orders');
  const [declared, setDeclared] = useState<Record<string,Model>>({});
  const [stage, setStage] = useState<StageResult|null>(null);
  const [build, setBuild] = useState<BuildResult|null>(null);
  const [buildRequest, setBuildRequest] = useState<BuildRequest|null>(null);
  const [metric, setMetric] = useState<Metric|null>(null);
  const [stepId, setStepId] = useState<string|null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [resetOpen, setResetOpen] = useState(false);
  useEffect(()=>{ let live=true; api<Scenario>('scenario').then(s=>{if(live)setScenario(s);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[]);
  useEffect(()=>{window.scrollTo(0,0);},[view]);
  async function act(operation:()=>Promise<void>) {setBusy(true);setError('');try{await operation();}catch(e){setError(e instanceof Error?e.message:'The operation failed.');}finally{setBusy(false);}}
  if(!scenario) return <main className="boot-screen"><div className="brand-mark"><FlaskConical size={26}/></div><h1>Modeling Lab</h1><p>{error || 'Loading the e-commerce learning workspace…'}</p>{error&&<button className="primary-button" onClick={()=>location.reload()}>Retry connection</button>}</main>;
  const sources=scenario.sources.map(s=>declared[s.id]??s);
  const models:Record<string,Model>=Object.fromEntries([...sources,...scenario.planned_models].map(m=>[m.id,m]));
  if(stage) models.stg_orders=stage.model;
  if(build) {models.stg_orders=build.staging;models.fct_orders=build.fact;}
  if(build) build.inputs.forEach(input=>{models[input.id]=declared[input.id]??input;});
  if(metric) models.revenue={...models.revenue,grain:{declared:'metric_value',label:'1 metric value',classification:'declared',status:metric.status,evidence:metric.evidence},status:metric.status,row_count:1,rows:[{revenue:metric.value,currency:metric.currency}],columns:[{name:'revenue',data_type:'DECIMAL',nullable:false,description:metric.description}]};
  const current=models[selected]??models.raw_orders;
  const steps:Step[]=build?.transformations??[stage?.transformation??scenario.transformations[0],...scenario.transformations.slice(1)];
  const detail=steps.find(s=>s.id===stepId)??(stepId?steps.find(s=>s.output_model===stepId):undefined);
  const flowModels=['raw_orders','stg_orders','fct_orders','revenue'].map(id=>models[id]);
  build?.fact.parents.forEach(id=>{if(!flowModels.some(m=>m.id===id)&&models[id])flowModels.push(models[id]);});
  const workflowDone=[declared.raw_orders?.status==='pass',!!stage,build?.evaluation.status==='pass',metric?.status==='pass'&&build?.evaluation.status==='pass'];
  function goStage(){setSelected('raw_orders');setView('story');}
  function reset(){setDeclared({});setStage(null);setBuild(null);setBuildRequest(null);setMetric(null);setSelected('raw_orders');setView('story');setStepId(null);setError('');setResetOpen(false);}
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#" onClick={e=>{e.preventDefault();setView('story');}}><span className="brand-mark"><FlaskConical size={23}/></span><span>Modeling<span className="brand-light">Lab</span><small>SEE THE REASONING</small></span></a>
      <div className="workspace-badge"><span className="workspace-icon"><Database size={17}/></span><div><strong>E-commerce</strong><span>Revenue foundations</span></div><ChevronRight size={15}/></div>
      <span className="nav-label">LEARNING WORKSPACE</span><nav aria-label="Learning workspace">{navigation.map(n=><button key={n.id} className={view===n.id?'active':''} onClick={()=>{setView(n.id);setError('');}}><n.icon size={19}/><span>{n.label}</span>{workflowDone[Number(n.number)-1]?<Check size={14} className="nav-check"/>:<small>{n.number}</small>}</button>)}</nav>
      <div className="sidebar-source-summary"><span className="nav-label">YOUR FIXTURE</span><div><Database size={15}/><span>6 source tables</span><span className="source-dot"/></div><p>Small enough to inspect.<br/>Real enough to challenge assumptions.</p></div>
      <div className="sidebar-bottom"><div className="sidebar-principle"><span>THE FIRST QUESTION</span><p>“What does<br/>one row represent?”</p><span className="principle-line"/></div><div className="local-label"><span/>Local & deterministic</div></div>
    </aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace<ChevronRight size={14}/><strong>E-commerce</strong><span className="lesson-badge">LAB 01</span></div><div className="topbar-actions"><div className="mode-switch" aria-label="Experience mode"><button aria-pressed={!advanced} className={!advanced?'active':''} onClick={()=>setAdvanced(false)}>Beginner</button><button aria-pressed={advanced} className={advanced?'active':''} onClick={()=>setAdvanced(true)}><Code2 size={13}/>Advanced</button></div><button className="icon-button" aria-label="Export evidence" disabled={busy} title="Export definitions and session evidence" onClick={()=>act(async()=>{const definitions=await api('contracts');download('modeling-lab-evidence.json',{definitions,declared_sources:declared,staging:stage,build,metric});})}><ArrowDownToLine size={18}/></button><button className="icon-button" aria-label="Reset session" title="Reset this learning session" disabled={busy} onClick={()=>setResetOpen(true)}><RotateCcw size={17}/></button></div></header>
    <main className="main-content">
      <div className="page-heading"><div><div className="page-eyebrow"><span/>DATA MODELING & TRANSFORMATION LAB</div><h1>From raw data to <em>trusted answers.</em></h1><p>Understand the grain. Follow the transformation. Prove the result.</p></div><div className="scenario-meta"><span className="scenario-icon"><Layers3 size={23}/></span><span><strong>E-commerce · 01</strong><small>Revenue foundations</small></span></div></div>
      <div className="journey-strip" aria-label="Session steps">{['Identify the grain','Clean the source','Build & verify','Define the metric'].map((l,i)=><div key={l} className={workflowDone[i]?'done':''}><span>{workflowDone[i]?<Check size={12}/>:i+1}</span>{l}{i<3&&<ChevronRight size={13}/>}</div>)}<span className="journey-note">Learn by doing</span></div>
      {error&&<div className="error-banner" role="alert"><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={()=>setError('')}><X size={15}/></button></div>}
      {view==='story'&&<div className="story-layout"><div className="story-main">
        <section className="card story-card"><div className="card-title"><div><span className="eyebrow">01 / THE TRANSFORMATION STORY</span><h2>Every arrow needs a reason.</h2></div><span className="tag"><span className="mini-dot"/>{build?'Executed design':stage?'Staging executed':'Your model, step by step'}</span></div><p className="muted story-intro">Turn operational order versions into one trustworthy revenue number. Select a model to inspect its meaning; select an arrow to see what changes.</p><StoryFlow models={flowModels} selected={selected} value={metric?.value} choose={setSelected} inspect={(source,target)=>setStepId(steps.find(s=>s.input_model===source&&s.output_model===target)?.id??null)}/><div className="arrow-actions">{['stg_orders','fct_orders','revenue'].map((id,i)=><button key={id} className={detail?.output_model===id?'selected':''} onClick={()=>setStepId(id)}><span>{['CLEAN','MODEL','MEASURE'][i]}</span><ArrowRight size={13}/>{['Why staging?','Why a fact?','Why a metric?'][i]}</button>)}</div></section>
        {detail&&<StepDetails step={detail} close={()=>setStepId(null)}/>}
        <section className="card source-section"><div className="card-title"><div><span className="eyebrow">THE RAW MATERIAL</span><h3>Six tables. Different row meanings.</h3></div><span className="tag">Synthetic, inspectable data</span></div><div className="source-grid">{sources.map(s=><button key={s.id} className={`source-card ${selected===s.id?'selected':''}`} onClick={()=>setSelected(s.id)}><div><Database size={16}/><strong>{s.name.replace('raw.','')}</strong><span>{s.row_count} rows</span></div><small>{s.columns.length} columns</small><StatusPill status={s.grain.status} label={s.grain.status==='unknown'?'GRAIN UNKNOWN':s.grain.status==='pass'?s.grain.label:'Declaration failed'}/></button>)}</div></section>
        <section className="card preview-card"><div className="card-title"><div><span className="eyebrow">LOOK AT THE RECORDS</span><h3><Table2 size={18}/>{current.name}</h3></div><span className="tag">{current.row_count??'—'} rows · {current.columns.length} columns</span></div>{current.id==='raw_orders'&&<p className="table-note"><KeyRound size={14}/>O1 appears twice. Is <code>orderId</code> alone a key for these source records?</p>}<Table rows={current.rows} columns={current.columns} repeatKey={current.id==='raw_orders'?'orderId':current.id==='fct_orders'?'order_id':undefined} caption={`${current.name} records`}/></section>
        <section className="card relationship-card"><div className="card-title"><h3>Designed relationships</h3><GitMerge size={18}/></div><div className="relationships">{scenario.relationships.map(r=><div key={r.id}><code>{r.left_model}.{r.left_key}</code><span className="cardinality-chip">{r.expected}</span><code>{r.right_model}.{r.right_key}</code><p>{r.description}</p></div>)}</div><button className="text-button" onClick={()=>setView('join')}>Experiment with a join<ArrowRight size={15}/></button></section>
      </div><GrainInspector key={current.id} model={current} busy={busy} advanced={advanced} ready={!!stage} onAdvanced={()=>setAdvanced(true)} declare={(grain,key)=>act(async()=>{const result=await api<GrainResult>('grain',{table:current.id,grain,primary_key:key});setDeclared(prev=>({...prev,[current.id]:result.model}));if(current.id==='raw_orders'){setStage(null);setBuild(null);setBuildRequest(null);setMetric(null);setStepId(null);}})} stage={()=>act(async()=>{const result=await api<StageResult>('staging',{source_grain:declared.raw_orders?.grain.declared});setStage(result);setBuild(null);setBuildRequest(null);setMetric(null);setSelected('stg_orders');setStepId('stg_orders');})}/></div>}
      {view==='join'&&<JoinLab scenario={scenario} advanced={advanced}/>}
      {view==='build'&&<BuildLab scenario={scenario} staged={!!stage} advanced={advanced} busy={busy} build={build} lastRequest={buildRequest} goStage={goStage} execute={request=>act(async()=>{const result=await api<BuildResult>('build',request);setBuild(result);setBuildRequest(request);setMetric(null);})}/>}
      {view==='metric'&&<MetricLab scenario={scenario} build={build} metric={metric} busy={busy} goBuild={()=>setView('build')} calculate={(name,aggregation)=>act(async()=>{if(!buildRequest)return;const result=await api<Metric>('metric',{build:buildRequest,name,aggregation});setMetric(result);})}/>}
      <footer className="workspace-footer"><span><FlaskConical size={14}/>Data Modeling Lab</span><span>Grain + keys + relationships + transformations + proof</span><span>First slice · v0.1</span></footer>
    </main></div>
    {resetOpen&&<div className="modal-backdrop"><section className="reset-dialog" role="dialog" aria-modal="true" aria-labelledby="reset-title"><RotateCcw size={26}/><h2 id="reset-title">Start the experiment again?</h2><p>This clears the current declarations, executed models, and metric. The fixture stays ready to explore.</p><div className="button-row"><button className="secondary-button" onClick={()=>setResetOpen(false)}>Keep exploring</button><button className="primary-button" onClick={reset}>Reset session</button></div></section></div>}
  </div>;
}
