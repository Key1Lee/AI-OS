import { useEffect, useMemo, useRef, useState } from 'react';
import { AIRFLOW_CONCEPTS, clockLabel, createRun, criticalPath, LEARNING_QUESTIONS, readinessExpectation, runningCount, scenarioContract, SCENARIO_INFO, stepSimulation, TASK_STATES, TODAY } from './engine';
import type { BackfillResult, RunTrigger, ScenarioId, SimulationRun, Stage, WorkflowDefinition } from './engine';
import { BackfillLab } from './ui/BackfillLab';
import { Icon, StageOverview, StateBadge, TaskGraph, TaskInspector, Timeline } from './ui/components';
import { LearningGuide } from './ui/LearningGuide';

type View = 'pipeline' | 'timeline' | 'backfill' | 'guide';
function freshRun(workflow: WorkflowDefinition, trigger: RunTrigger, workers: number, number: number, previous?: SimulationRun) {
  return createRun(workflow, { partition: TODAY, clock_date: TODAY, start_minute: 355, trigger, max_concurrency: workers,
    run_id: `${workflow.id}:${TODAY}:run-${number}`, initial_outputs: previous?.outputs });
}
function downloadJson(name: string, payload: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function App() {
  const [scenarioId, setScenarioId] = useState<ScenarioId>('healthy');
  const contract = useMemo(() => scenarioContract(scenarioId), [scenarioId]), workflow = contract.workflow;
  const [trigger, setTrigger] = useState<RunTrigger>({ kind: 'daily' }), [workers, setWorkers] = useState(2);
  const counter = useRef(1);
  const [run, setRun] = useState(() => freshRun(workflow, trigger, workers, 1));
  const [playing, setPlaying] = useState(false), [advanced, setAdvanced] = useState(false);
  const [view, setView] = useState<View>('pipeline'), [detailed, setDetailed] = useState(false), [assets, setAssets] = useState(false);
  const [selected, setSelected] = useState('extract_orders'), [highlight, setHighlight] = useState(false);
  const [history, setHistory] = useState<SimulationRun[]>([]), [prediction, setPrediction] = useState(false);
  const [backfillEvidence, setBackfillEvidence] = useState<BackfillResult | null>(null);
  useEffect(() => {
    if (!playing || run.complete) return;
    const timer = window.setInterval(() => setRun(previous => stepSimulation(previous, workflow)), 380);
    return () => window.clearInterval(timer);
  }, [playing, run.complete, workflow]);
  useEffect(() => {
    if (!run.complete) return;
    setPlaying(false);
    setHistory(previous => previous.some(r => r.run_id === run.run_id) ? previous : [...previous, run]);
  }, [run]);
  function reset(clearOutputs = true) {
    setPlaying(false); setPrediction(false);
    if (clearOutputs) { counter.current = 1; setHistory([]); }
    else counter.current++;
    setRun(freshRun(workflow, trigger, workers, counter.current, clearOutputs ? undefined : run));
  }
  function changeScenario(id: ScenarioId) {
    setPlaying(false); setScenarioId(id); counter.current = 1; setHistory([]); setPrediction(false);
    setRun(freshRun(scenarioContract(id).workflow, trigger, workers, 1));
  }
  function changeSettings(nextTrigger: RunTrigger, nextWorkers: number) {
    setPlaying(false); setTrigger(nextTrigger); setWorkers(nextWorkers); setHistory([]); counter.current = 1;
    setRun(freshRun(workflow, nextTrigger, nextWorkers, 1));
  }
  function runOrPause() {
    if (playing) { setPlaying(false); return; }
    if (run.complete) reset(false);
    setPlaying(true);
  }
  function reveal(stage?: Stage) {
    setDetailed(true); setAssets(false);
    if (stage) setSelected(workflow.tasks.find(t => t.stage === stage)!.id);
  }
  function chooseTask(id: string) { setSelected(id); setDetailed(true); setView('pipeline'); }
  const critical = criticalPath(workflow), expectation = readinessExpectation(run, workflow);
  const succeeded = Object.values(run.tasks).filter(t => t.status === 'SUCCESS').length;
  const blocked = Object.values(run.tasks).filter(t => t.status === 'BLOCKED').length;
  const latest = history.at(-1), first = history[0];
  const rowCount = (r: SimulationRun | undefined) => r?.outputs.mart_revenue?.[TODAY];
  const info = SCENARIO_INFO.find(s => s.id === scenarioId)!;
  const triggerLabel = trigger.kind === 'daily' ? 'daily' : trigger.kind === 'manual' ? 'manual' : 'asset';
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setView('pipeline'); }}><span className="brand-mark"><Icon name="flow" size={24}/></span><span>Data Pipeline<span>& Orchestration Lab</span></span></a>
      <div className="sidebar-label">LEARNING WORKSPACE</div>
      <nav aria-label="Lab views">{([{ id: 'pipeline', title: 'Pipeline simulator', icon: 'flow' }, { id: 'timeline', title: 'Execution timeline', icon: 'clock' }, { id: 'backfill', title: 'Backfill Lab', icon: 'calendar' }, { id: 'guide', title: 'Learning guide', icon: 'book' }] as const).map(item => <button className={view === item.id ? 'active' : ''} key={item.id} onClick={() => setView(item.id)} aria-current={view === item.id ? 'page' : undefined}><Icon name={item.icon}/>{item.title}{item.id === 'backfill' && <span className="nav-dot"/>}</button>)}</nav>
      <div className="sidebar-questions"><div className="sidebar-label">EIGHT QUESTIONS, EVERY RUN</div>{LEARNING_QUESTIONS.map((question, i) => <div key={question}><span>{String(i + 1).padStart(2, '0')}</span>{question}</div>)}</div>
      <div className="sidebar-boundary"><span className="sidebar-label">ONE CLEAR RESPONSIBILITY</span><strong>When, why, and in what order?</strong><p>Modeling defines the data.<br/>Orchestration runs the work.<br/>Observability reads the evidence.<br/>Toptal assesses the reasoning.</p></div>
      <div className="sidebar-footer"><span className="online-dot"/>Local simulator<span>v0.1</span></div>
    </aside>
    <main>
      <header className="topbar"><div className="breadcrumb">Learning lab <Icon name="chevron" size={12}/><strong>Orchestration basics</strong></div><div className="topbar-right"><span className="offline-pill"><span className="online-dot"/>Deterministic · offline</span><div className="mode-switch" role="group" aria-label="Learning mode"><button className={!advanced ? 'active' : ''} onClick={() => setAdvanced(false)}>Beginner</button><button className={advanced ? 'active' : ''} onClick={() => setAdvanced(true)}>Advanced</button></div></div></header>
      <div className="workspace">
        <div className="page-heading"><div><span className="eyebrow">UNDERSTAND THE ORDER OF WORK</span><h1>{view === 'backfill' ? 'Reprocess the past.' : view === 'timeline' ? 'Watch time shape the run.' : view === 'guide' ? 'Build your mental model.' : 'See the pipeline. Explain the run.'}</h1><p>Small workflows. Clear dependencies. Every outcome has a reason.</p></div><button className="button secondary export-button" disabled={view === 'backfill' && !backfillEvidence} onClick={() => view === 'backfill' ? downloadJson('backfill-evidence.json', { contract_version: 'orchestration-backfill-session-v1', ...backfillEvidence }) : downloadJson('orchestration-evidence.json', { contract_version: 'orchestration-session-v1', scenario: contract, run, history })}><Icon name="download" size={16}/>{view === 'backfill' ? 'Export backfill evidence' : 'Export run evidence'}</button></div>
        <div className="compact-questions"><span className="eyebrow">EIGHT QUESTIONS, EVERY RUN</span><div>{LEARNING_QUESTIONS.map((question, i) => <span key={question}><small>{i + 1}</small>{question}</span>)}</div></div>
        {view !== 'backfill' && view !== 'guide' && <>
          <section className="run-console panel" aria-label="Simulation controls">
            <div className="console-top"><div className="workflow-title"><span className="workflow-icon"><Icon name="flow" size={21}/></span><div><h2>{workflow.name}</h2><span>Partition · Oct 2, 2026 <span className="dot-divider">·</span> {workflow.tasks.length} tasks</span></div></div><div className="clock-display"><Icon name="clock" size={19}/><strong data-testid="virtual-clock">{clockLabel(run.now)}</strong><span>VIRTUAL TIME<br/>Asia/Seoul</span></div></div>
            <div className="console-controls"><label className="scenario-select"><span>Scenario</span><select aria-label="Learning scenario" value={scenarioId} disabled={playing} onChange={e => changeScenario(e.target.value as ScenarioId)}>{SCENARIO_INFO.map(s => <option value={s.id} key={s.id}>{s.title}</option>)}</select></label>
              <label><span>Workflow trigger</span><select aria-label="Workflow trigger" value={triggerLabel} disabled={playing} onChange={e => changeSettings(e.target.value === 'asset' ? { kind: 'asset', asset_id: 'source.orders' } : { kind: e.target.value as 'daily' | 'manual' }, workers)}><option value="daily">Daily · 06:00</option><option value="manual">Manual · now</option><option value="asset">Orders asset updated</option></select></label>
              <label className="worker-select"><span>Workers</span><select aria-label="Available workers" value={workers} disabled={playing} onChange={e => changeSettings(trigger, Number(e.target.value))}>{[1, 2, 3, 4].map(n => <option key={n}>{n}</option>)}</select></label>
              <div className="playback-controls"><button className="button primary" onClick={runOrPause}><Icon name={playing ? 'pause' : 'play'} size={15}/>{playing ? 'Pause' : run.complete ? 'Run again' : 'Run simulation'}</button><button className="button secondary" onClick={() => setRun(previous => stepSimulation(previous, workflow))} disabled={playing || run.complete}><Icon name="step" size={15}/>Step</button><button className="icon-button" aria-label="Reset simulation" title="Reset simulation and output state" onClick={() => reset()}><Icon name="reset" size={18}/></button></div>
            </div>
            <div className="run-summary" aria-live="polite"><span><span className={`summary-dot ${run.status.toLowerCase()}`}/>{run.complete ? run.status === 'SUCCESS' ? 'Workflow complete' : 'Workflow ended with a failure' : run.activated ? 'Workflow running' : trigger.kind === 'daily' ? 'Scheduled for 06:00 · not yet eligible' : 'Explicit trigger accepted · ready to start'}</span><span><Icon name="workers" size={14}/>{runningCount(run)}/{workers} workers in use</span><span>{succeeded}/{workflow.tasks.length} succeeded{blocked > 0 ? ` · ${blocked} blocked` : ''}</span></div>
          </section>
          <div className="scenario-brief"><div className="brief-icon"><Icon name="help" size={23}/></div><div><span className="eyebrow">PREDICT → RUN → EXPLAIN</span><strong>{info.short}</strong><p>{info.description}</p></div><button className="text-button" onClick={() => setPrediction(p => !p)}>{prediction ? 'Hide prompt' : 'Make a prediction'}<Icon name="chevron" size={14}/></button></div>
          {prediction && <div className="prediction-prompt">Before running: which tasks can start together, which must wait, and what would be blocked if customer extraction failed? Compare your reasoning with the task inspector. Scoring belongs to Toptal.</div>}
        </>}
        {view === 'pipeline' && <>
          <section className="pipeline-panel panel"><div className="panel-heading"><div><span className="eyebrow">{detailed ? assets ? 'ASSETS ARE DATA; TASKS CREATE THEM' : 'THE TASK DEPENDENCY GRAPH' : 'START WITH THE BIG PICTURE'}</span><h2>{detailed ? assets ? 'What the work produces' : 'What must happen first' : 'One workflow. Six clear stages.'}</h2></div><div className="graph-view-controls"><div className="segmented" role="group" aria-label="Graph view"><button className={!detailed ? 'active' : ''} onClick={() => { setDetailed(false); setAssets(false); }}>Stages</button><button className={detailed && !assets ? 'active' : ''} onClick={() => reveal()}>Tasks</button><button className={assets ? 'active' : ''} onClick={() => { setDetailed(true); setAssets(true); }}>Assets</button></div></div></div>
            {!detailed ? <StageOverview workflow={workflow} run={run} onReveal={reveal}/> : <TaskGraph workflow={workflow} run={run} selected={selected} onSelect={setSelected} assets={assets} showCritical={highlight}/>}
            <div className="graph-bottom"><span><Icon name="help" size={14}/>{detailed ? 'Click any task or asset to explain its execution state.' : 'Start simple. Click a stage to reveal the actual tasks.'}</span>{detailed ? <label className="checkbox"><input type="checkbox" checked={highlight} onChange={e => setHighlight(e.target.checked)}/>Show critical path · {critical.minutes}m</label> : <button className="text-button" onClick={() => reveal()}>Reveal {workflow.tasks.length} tasks<Icon name="arrow" size={15}/></button>}</div>
            <div className="state-legend" aria-label="Execution states">{TASK_STATES.map(status => <StateBadge key={status} status={status}/>)}</div>
          </section>
          <TaskInspector workflow={workflow} run={run} selected={selected} advanced={advanced}/>
          <div className="learning-cards"><section className="panel rerun-card"><span className="eyebrow">CAN IT SAFELY RUN TWICE?</span><h2>Same inputs. Same correct state?</h2><p className="muted">The mart uses an authored 100-row payload. {scenarioId === 'unsafe-rerun' ? 'Appending the same payload can create duplicates.' : 'Replacing this partition makes the rerun safe.'}</p><div className="row-comparison"><div><span>RUN #1</span><strong data-testid="first-row-count">{rowCount(first) ?? '—'}<small>rows</small></strong></div><Icon name="arrow" size={24}/><div><span>{history.length > 1 ? `RUN #${history.length}` : 'RUN #2'}</span><strong data-testid="latest-row-count">{history.length > 1 ? rowCount(latest) ?? '—' : '—'}<small>rows</small></strong></div><span className={`comparison-label ${scenarioId === 'unsafe-rerun' ? 'unsafe' : ''}`}>{history.length > 1 ? scenarioId === 'unsafe-rerun' ? 'Duplicates accumulate' : 'State is preserved' : 'Compare two runs'}</span></div><button className="button secondary" disabled={!run.complete} onClick={() => { reset(false); setPlaying(true); }}><Icon name="reset" size={15}/>Rerun same inputs</button></section>
            <section className="panel critical-card"><span className="eyebrow">WHICH BRANCH SETS THE PACE?</span><h2>The dependency critical path</h2><div className="critical-value"><strong>{critical.minutes}<small>min</small></strong><span>Minimum duration<br/>with unlimited workers</span></div><p className="small critical-chain">{critical.tasks.join(' → ')}</p><p className="small muted">Speeding up a shorter parallel branch may not help. Retry delays and limited workers can make the real run longer.</p><button className="text-button" onClick={() => setView('timeline')}>See the execution timeline<Icon name="arrow" size={15}/></button></section>
          </div>
          {run.complete && run.status === 'FAILED' && scenarioId === 'customer-failure' && <div className="repair-banner"><div><strong>Retries cannot repair this configuration error.</strong><span>Fix the authored customer source configuration, then rerun the whole workflow.</span></div><button className="button primary" onClick={() => { changeScenario('healthy'); setPlaying(true); }}>Fix configuration & rerun</button></div>}
          <div className="expectation-note"><Icon name="clock" size={16}/><span>Dashboard expected ready · <strong>07:00</strong></span><span>Actual · <strong>{expectation.actual === null ? 'Not ready' : clockLabel(expectation.actual)}</strong></span><span>{expectation.delay_minutes === null ? 'Readiness is an execution fact.' : `${expectation.delay_minutes} minutes late`}</span></div>
        </>}
        {view === 'timeline' && <Timeline workflow={workflow} run={run} onSelect={chooseTask}/>}
        <div hidden={view !== 'backfill'}><BackfillLab onResultChange={setBackfillEvidence}/></div>
        {view === 'guide' && <LearningGuide/>}
        {advanced && view !== 'backfill' && view !== 'guide' && <section className="panel advanced-panel"><div className="panel-heading"><div><span className="eyebrow">SAME TRUTH, MORE DETAIL</span><h2>Contracts & execution evidence</h2></div><Icon name="code" size={22}/></div><p className="muted">Execution events go to Observability. Scenario definitions and deterministic evidence go to Toptal. All grading, hints, incidents, and transformation semantics stay with their owners.</p><div className="advanced-actions"><button className="button secondary" onClick={() => downloadJson('execution-events.json', run.events)}>Export execution events</button><button className="button secondary" onClick={() => downloadJson('orchestration-scenario.json', contract)}>Export scenario contract</button></div><details><summary>Execution events · {run.events.length}</summary><pre>{JSON.stringify(run.events, null, 2)}</pre></details><details><summary>Vendor-neutral workflow definition</summary><pre>{JSON.stringify(workflow, null, 2)}</pre></details><details><summary>Airflow concept mapping · future adapter</summary><div className="concept-mapping">{Object.entries(AIRFLOW_CONCEPTS).map(([generic, airflow]) => <div key={generic}><span>{generic}</span><Icon name="arrow" size={14}/><strong>{airflow}</strong></div>)}</div><p className="small muted">Airflow, Dagster, Prefect, and dbt jobs adapters are design boundaries; no vendor integration runs in this slice.</p></details></section>}
        <footer className="workspace-footer"><span><Icon name="flow" size={13}/>Data Orchestration Lab</span><span>Explicit inputs. Repeatable results. No production orchestrator.</span></footer>
      </div>
    </main>
  </div>;
}
