import { useId } from 'react';
import { clockLabel, criticalPath, downstream, whyTask } from '../engine';
import type { SimulationRun, Stage, TaskStatus, WorkflowDefinition } from '../engine';

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    flow: <><rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="15" y="15" width="6" height="6" rx="1.5"/><path d="M6 9v9h9M9 6h9v9"/></>,
    play: <path d="m8 5 11 7-11 7Z"/>, pause: <><path d="M8 5v14M16 5v14"/></>,
    step: <><path d="m5 5 10 7-10 7ZM19 5v14"/></>, reset: <><path d="M3 10a9 9 0 1 1 2 8M3 4v6h6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M7 14h3M14 14h3M7 18h3"/></>,
    layers: <><path d="m12 3 10 5-10 5L2 8ZM2 12l10 5 10-5M2 16l10 5 10-5"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>, chevron: <path d="m9 5 7 7-7 7"/>,
    download: <><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/></>,
    book: <><path d="M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1ZM12 5v15"/></>,
    check: <path d="m5 12 4 4L19 6"/>, spark: <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>,
    code: <><path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/></>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 4 3c-1 .5-1 1-1 2M12 17v.1"/></>,
    workers: <><circle cx="8" cy="7" r="3"/><path d="M2 20v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M17 13a5 5 0 0 1 5 5v2"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.flow}</svg>;
}
export const STATE_SYMBOL: Record<TaskStatus, string> = { WAITING: '○', READY: '◇', RUNNING: '●', SUCCESS: '✓', FAILED: '×', RETRYING: '↻', BLOCKED: '⊘', SKIPPED: '−' };
export function StateBadge({ status }: { status: TaskStatus }) {
  return <span className={`state-badge state-${status.toLowerCase()}`}><span aria-hidden="true">{STATE_SYMBOL[status]}</span>{status}</span>;
}
export const STAGES: { id: Stage | 'source'; title: string; subtitle: string }[] = [
  { id: 'source', title: 'Source', subtitle: 'Data is available' }, { id: 'ingest', title: 'Ingest', subtitle: 'Bring data in' },
  { id: 'staging', title: 'Staging', subtitle: 'Prepare the inputs' }, { id: 'transform', title: 'Transform', subtitle: 'Build declared models' },
  { id: 'mart', title: 'Mart', subtitle: 'Publish for a purpose' }, { id: 'dashboard', title: 'Dashboard', subtitle: 'Make it usable' },
];
export function stageStatus(workflow: WorkflowDefinition, run: SimulationRun, stage: Stage): TaskStatus {
  const states = workflow.tasks.filter(t => t.stage === stage).map(t => run.tasks[t.id].status);
  for (const state of ['FAILED', 'RUNNING', 'RETRYING', 'BLOCKED', 'READY', 'WAITING'] as TaskStatus[]) if (states.includes(state)) return state;
  return states.every(s => s === 'SKIPPED') ? 'SKIPPED' : 'SUCCESS';
}

export function StageOverview({ workflow, run, onReveal }: { workflow: WorkflowDefinition; run: SimulationRun; onReveal: (stage?: Stage) => void }) {
  return <div className="stage-overview" aria-label="Beginner pipeline overview">
    {STAGES.map((stage, index) => <div key={stage.id} className="stage-unit">
      <button className={`stage-card ${stage.id === 'source' ? 'source-card' : `border-${stageStatus(workflow, run, stage.id).toLowerCase()}`}`} onClick={() => onReveal(stage.id === 'source' ? 'ingest' : stage.id)} aria-label={`Explore ${stage.title}`}>
        <span className="stage-number">0{index + 1}</span><Icon name={stage.id === 'source' ? 'layers' : stage.id === 'dashboard' ? 'spark' : 'flow'} size={25}/>
        <strong>{stage.title}</strong><span className="stage-subtitle">{stage.subtitle}</span>
        {stage.id === 'source' ? <span className="source-label">2 source feeds</span> : <StateBadge status={stageStatus(workflow, run, stage.id)}/>}
      </button>{index < STAGES.length - 1 && <span className="stage-arrow"><Icon name="arrow"/></span>}
    </div>)}
  </div>;
}

const POSITIONS: Record<string, [number, number]> = {
  extract_orders: [16, 34], extract_customers: [16, 234], stg_orders: [190, 34], stg_customers: [190, 234],
  int_orders: [364, 94], quality_check: [364, 254], fct_orders: [538, 134], mart_revenue: [712, 134], dashboard: [886, 134],
};
const NODE_WIDTH = 152, NODE_HEIGHT = 100;
export function TaskGraph({ workflow, run, selected, onSelect, assets, showCritical }: { workflow: WorkflowDefinition; run: SimulationRun; selected: string; onSelect: (id: string) => void; assets: boolean; showCritical: boolean }) {
  const marker = useId().replace(/:/g, '');
  const path = criticalPath(workflow).tasks;
  return <div className="graph-scroll" tabIndex={0} aria-label={assets ? 'Data asset dependency graph' : 'Task dependency graph'}>
    <div className="task-graph">
      <div className="graph-lane-label" style={{ left: 16 }}>INGEST</div><div className="graph-lane-label" style={{ left: 190 }}>STAGING</div>
      <div className="graph-lane-label" style={{ left: 364 }}>TRANSFORM</div><div className="graph-lane-label" style={{ left: 712 }}>MART</div><div className="graph-lane-label" style={{ left: 886 }}>OUTPUT</div>
      <svg className="graph-arrows" width="1054" height="390" aria-hidden="true">
        <defs><marker id={marker} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#91a0ae"/></marker><marker id={`${marker}c`} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#d2923b"/></marker></defs>
        {workflow.tasks.flatMap(task => task.dependencies.map(parent => {
          const [px, py] = POSITIONS[parent], [x, y] = POSITIONS[task.id];
          const x1 = px + NODE_WIDTH, y1 = py + NODE_HEIGHT / 2, x2 = x - 5, y2 = y + NODE_HEIGHT / 2;
          const isCritical = showCritical && path.includes(task.id) && path.includes(parent) && path.indexOf(task.id) === path.indexOf(parent) + 1;
          return <path key={`${parent}-${task.id}`} d={`M${x1} ${y1} C${x1 + 22} ${y1},${x2 - 22} ${y2},${x2} ${y2}`} fill="none" stroke={isCritical ? '#d2923b' : '#b8c4d0'} strokeWidth={isCritical ? 2.8 : 1.6} markerEnd={`url(#${marker}${isCritical ? 'c' : ''})`} />;
        }))}
      </svg>
      {workflow.tasks.map(task => {
        const [x, y] = POSITIONS[task.id], execution = run.tasks[task.id];
        return <button key={task.id} data-testid={`task-${task.id}`} className={`task-node border-${execution.status.toLowerCase()} ${selected === task.id ? 'selected' : ''} ${assets ? 'asset-node' : ''}`} style={{ left: x, top: y, width: NODE_WIDTH }} onClick={() => onSelect(task.id)} aria-pressed={selected === task.id}>
          <span className="node-kind">{assets ? 'DATA ASSET' : 'TASK'}<span>{task.duration_minutes}m</span></span>
          <strong>{assets ? task.outputs[0] : task.name}</strong><StateBadge status={execution.status}/>
          {assets && <span className="asset-producer">created by {task.name}</span>}
        </button>;
      })}
    </div>
  </div>;
}

function displayTime(time: string | null) { return time ? time.slice(11, 16) : '—'; }
export function TaskInspector({ workflow, run, selected, advanced }: { workflow: WorkflowDefinition; run: SimulationRun; selected: string; advanced: boolean }) {
  const task = workflow.tasks.find(t => t.id === selected)!, execution = run.tasks[selected], explanation = whyTask(run, workflow, selected);
  const affected = downstream(workflow, selected);
  return <section className="inspector panel" data-testid="task-inspector" aria-label="Task details">
    <div className="panel-heading"><div><span className="eyebrow">TASK INSPECTOR</span><h2>{task.name}</h2></div><StateBadge status={execution.status}/></div>
    <p className="muted task-purpose">{task.purpose}</p>
    <div className="inspector-grid">
      <div>
        <div className={`explanation explanation-${execution.status.toLowerCase()}`}><span className="eyebrow">WHY HASN’T THIS RUN?</span><strong>{explanation.title}</strong><p>{explanation.detail}</p></div>
        <div className="dependency-heading"><h3>What must finish first?</h3><span>{task.trigger_rule === 'all_success' ? 'ALL MUST SUCCEED' : task.trigger_rule.toUpperCase().replace('_', ' ')}</span></div>
        {explanation.dependencies.length ? <div className="dependency-list">{explanation.dependencies.map(dep => <div key={dep.id}><code>{dep.id}</code><StateBadge status={dep.status}/></div>)}</div> : <p className="small muted">No upstream tasks. The workflow trigger and capacity are enough.</p>}
      </div>
      <div className="task-facts">
        <div className="facts-grid"><div><span>Started</span><strong>{displayTime(execution.start_time)}</strong></div><div><span>Finished</span><strong>{displayTime(execution.end_time)}</strong></div><div><span>Attempt duration</span><strong>{execution.duration === null ? '—' : `${execution.duration} min`}</strong></div><div><span>Attempt</span><strong>{execution.execution_attempt} / {task.retry_policy.max_attempts}</strong></div></div>
        <div className="fact-row"><span>When</span><strong>{run.trigger.kind === 'daily' ? `Daily ${workflow.schedule.time} · ${workflow.schedule.timezone}` : run.trigger.kind === 'manual' ? 'Manual workflow trigger' : `${run.trigger.asset_id} updated · data event`}</strong></div>
        <div className="fact-row"><span>Retry</span><strong>Temporary errors · wait {task.retry_policy.delay_minutes} min</strong></div>
        <div className="fact-row"><span>Timeout</span><strong>{task.timeout_minutes} min per attempt</strong></div>
        <div className="fact-row"><span>Safe to run twice?</span><strong className={task.idempotent === false ? 'text-danger' : 'text-teal'}>{task.idempotent === 'unknown' ? 'Unknown' : task.idempotent ? 'Yes · replaces this partition' : 'No · appends the same rows'}</strong></div>
        <div className="asset-contract"><span>Inputs → task → output asset</span><code>{task.inputs.join(' + ') || 'none'}</code><Icon name="arrow" size={15}/><code>{task.outputs.join(', ')}</code></div>
      </div>
    </div>
    <div className="inspector-footer"><strong>What gets blocked downstream?</strong><div className="downstream-tasks">{affected.length ? affected.map(id => <span key={id}><code>{id}</code><StateBadge status={run.tasks[id].status}/></span>) : 'Nothing. This is an end task.'}</div></div>
    {execution.attempts.length > 0 && <div className="attempts-strip">{execution.attempts.map(attempt => <div key={attempt.attempt} className={`attempt-mini state-${attempt.status.toLowerCase()}`}><strong>Attempt {attempt.attempt} · {attempt.status}</strong><span>{displayTime(attempt.start_time)} → {displayTime(attempt.end_time)}{attempt.error ? ` · ${attempt.error.message}` : ''}</span></div>)}</div>}
    {advanced && <details className="advanced-details"><summary>Task definition and execution state</summary><pre>{JSON.stringify({ definition: task, execution }, null, 2)}</pre></details>}
  </section>;
}

export function Timeline({ workflow, run, onSelect }: { workflow: WorkflowDefinition; run: SimulationRun; onSelect: (id: string) => void }) {
  const attempts = Object.values(run.tasks).flatMap(t => t.attempts);
  const start = Math.min(360, ...attempts.map(a => a.start_minute)), end = Math.max(start + 20, run.now + 1, ...attempts.map(a => a.end_minute ?? run.now));
  const range = end - start, path = criticalPath(workflow);
  return <section className="panel timeline-panel"><div className="panel-heading"><div><span className="eyebrow">EXECUTION OVER TIME</span><h2>Every attempt has a place.</h2></div><span className="label">Virtual minutes</span></div>
    <p className="muted">Solid bars are attempts. Dashed spaces show the wait between attempts, including retry delay and any wait for capacity. The gold marker identifies the dependency critical path.</p>
    <div className="timeline-scroll"><div className="timeline"><div className="timeline-axis"><span>Task / attempt</span><div>{[0, 1, 2, 3, 4].map(i => <span key={i} style={{ left: `${i * 25}%` }}>{clockLabel(Math.round(start + range * i / 4))}</span>)}</div></div>
      {workflow.tasks.map(task => <div className="timeline-row" key={task.id}><button onClick={() => onSelect(task.id)} className="timeline-task"><span className={path.tasks.includes(task.id) ? 'critical-dot' : 'neutral-dot'}/><code>{task.name}</code></button><div className="timeline-track">
        {[0, 1, 2, 3, 4].map(i => <span className="time-gridline" style={{ left: `${i * 25}%` }} key={i}/>)}
        {run.tasks[task.id].attempts.map((attempt, index, all) => <div key={attempt.attempt}>
          {index > 0 && <span className="retry-gap" style={{ left: `${(all[index - 1].end_minute! - start) / range * 100}%`, width: `${(attempt.start_minute - all[index - 1].end_minute!) / range * 100}%` }} title={`Between attempts: ${task.retry_policy.delay_minutes}m retry delay + ${Math.max(0, attempt.start_minute - all[index - 1].end_minute! - task.retry_policy.delay_minutes)}m waiting for capacity.`}/>}
          <span className={`timeline-bar state-${attempt.status.toLowerCase()}`} style={{ left: `${(attempt.start_minute - start) / range * 100}%`, width: `${Math.max(.3, (attempt.end_minute ?? run.now) - attempt.start_minute) / range * 100}%` }} title={`Attempt ${attempt.attempt}: ${attempt.status}, ${attempt.duration ?? run.now - attempt.start_minute} minutes`}>{attempt.attempt}</span>
        </div>)}
        {run.tasks[task.id].attempts.length === 0 && <span className="timeline-empty">{run.tasks[task.id].status === 'BLOCKED' ? '⊘ Blocked · never started' : run.tasks[task.id].status.toLowerCase()}</span>}
      </div></div>)}
    </div></div><div className="timeline-note"><span className="critical-dot"/><strong>Dependency critical path · {path.minutes} min</strong><span>{path.tasks.join(' → ')}</span></div>
    <p className="small muted">This is the minimum with unlimited workers and no retries. Actual completion can take longer because of worker limits, retry delays, or failures.</p>
  </section>;
}
