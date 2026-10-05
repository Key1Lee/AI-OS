import { useEffect, useState } from 'react';
import { ArrowRight, CircleCheck, Code2, GitMerge, Play, RotateCcw, ShieldCheck, TriangleAlert } from 'lucide-react';
import { api } from './api';
import { Proofs, SqlBlock, StatusPill, Table } from './components';
import type { BuildRequest, BuildResult, Cardinality, JoinRequest, JoinResult, Metric, Scenario } from './types';

export function JoinLab({ scenario, advanced }: { scenario: Scenario; advanced: boolean }) {
  const [config, setConfig] = useState<JoinRequest>({ left_table: 'completed_orders', right_table: 'order_items', left_key: 'order_id', right_key: 'order_id', kind: 'left', aggregate_right: false, expected_cardinality: 'N:1', expected_rows: 3 });
  const [result, setResult] = useState<JoinResult | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true; setResult(null); setError('');
    api<JoinResult>('join', config).then(r => { if (live) setResult(r); }).catch(e => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [config]);
  const right = scenario.sources.find(s => s.id === config.right_table)!;
  function changeRight(value: string) {
    const customer = value === 'customers';
    setConfig({ ...config, right_table: value, left_key: customer ? 'customer_id' : 'order_id', right_key: customer ? 'customer_id' : 'order_id', aggregate_right: false });
  }
  return <div className="lab-view">
    <div className="section-heading"><div><span className="eyebrow">02 / EXPERIMENT</span><h2>A join is a change in row shape.</h2><p>Follow an order into every matching record. See exactly where its amount repeats.</p></div><span className="tag"><GitMerge size={14}/> Join cardinality lab</span></div>
    <section className="card join-controls" aria-label="Join controls">
      <label>Left dataset<select aria-label="Left dataset" value={config.left_table} onChange={e => setConfig({...config, left_table:e.target.value, expected_rows:e.target.value === 'stg_orders' ? 4 : e.target.value === 'order_items' ? 5 : 3, ...(e.target.value==='order_items'?{left_key:'order_id',right_key:'order_id',right_table:'payments',aggregate_right:false}:{})})}><option value="completed_orders">Completed orders · 3 rows</option><option value="stg_orders">All staged orders · 4 rows</option><option value="order_items">Order items · 5 rows · explore N:N</option></select></label>
      <label>Right dataset<select aria-label="Right dataset" value={config.right_table} onChange={e => changeRight(e.target.value)}>{['order_items','customers','payments','returns'].map(t => <option key={t} value={t}>{t}</option>)}</select></label>
      <label>Join type<select aria-label="Join type" value={config.kind} onChange={e => setConfig({...config, kind:e.target.value as 'left'|'inner'})}><option value="left">LEFT · keep unmatched</option><option value="inner">INNER · matched only</option></select></label>
      <label>Expected cardinality<select aria-label="Expected cardinality" value={config.expected_cardinality} onChange={e => setConfig({...config, expected_cardinality:e.target.value as Cardinality})}>{['1:1','1:N','N:1','N:N'].map(c => <option key={c}>{c}</option>)}</select></label>
      <label>Expected rows<input aria-label="Expected rows" type="number" min="0" max="1000" value={config.expected_rows} onChange={e => setConfig({...config, expected_rows:Math.min(1000,Math.max(0,Number(e.target.value)))})}/></label>
      <div className="join-key-line"><span><code>{config.left_key}</code><ArrowRight size={14}/><code>{config.right_key}</code></span><label className="check-label"><input type="checkbox" checked={config.aggregate_right} onChange={e => setConfig({...config, aggregate_right:e.target.checked, expected_cardinality:e.target.checked ? config.left_table==='order_items'||config.left_key==='customer_id'?'N:1':'1:1' : 'N:1'})}/>Aggregate right side to its join key first</label></div>
    </section>
    {error && <div className="error-banner" role="alert">{error}</div>}
    {!result && !error && <div className="card loading-inline" role="status">Executing the join…</div>}
    {result && <>
      <div className={`join-outcome ${result.fanout ? 'warning' : 'pass'}`}>
        <div>{result.fanout ? <TriangleAlert size={22}/> : <CircleCheck size={22}/>}<span><strong>{result.fanout ? 'Grain changed. Every right match creates another copy of the left row.' : 'The join preserves each left row’s grain.'}</strong><p>{result.explanation}</p></span></div>
        <StatusPill status={result.fanout ? 'warning' : 'pass'} label={result.fanout ? 'FANOUT' : 'GRAIN PRESERVED'}/>
      </div>
      <div className="join-stat-grid">
        <div className="stat-card"><small>LEFT ROWS</small><strong>{result.left_rows}</strong><span>{result.left_grain}</span></div>
        <div className="stat-card"><small>RIGHT ROWS</small><strong>{result.right_rows_after}{config.aggregate_right && <em> / {result.right_rows} before</em>}</strong><span>{result.right_grain}</span></div>
        <div className="stat-card"><small>ACTUAL CARDINALITY</small><strong>{result.actual_cardinality}</strong><span>Expected {result.expected_cardinality} · matched keys</span></div>
        <div className={`stat-card ${result.actual_rows !== result.expected_rows ? 'warn' : ''}`}><small>JOINED ROWS</small><strong data-testid="join-row-count">{result.actual_rows}</strong><span>{result.expected_rows} expected · {result.calculated_rows} independently calculated</span></div>
      </div>
      <section className="card"><div className="card-title"><div><span className="eyebrow">FOLLOW THE ROW</span><h3>Follow each key. Count every match.</h3></div><span className="tag">Observed fixture evidence</span></div>
        <div className="join-traces">{result.trace.map((trace,i) => <div key={i} className={`join-trace ${trace.repeated ? 'repeated' : ''}`}>
          <div className="trace-source"><strong>{String(trace.key ?? 'NULL')}</strong><span>{trace.left_rows} left {trace.left_rows === 1 ? 'row' : 'rows'}{trace.order_amount !== null && ` · $${trace.order_amount}${trace.left_rows>1?' total':''}`}</span></div>
          <div className="trace-operation"><span>{trace.right_rows} {trace.right_rows === 1 ? 'match' : 'matches'}</span><ArrowRight size={20}/></div>
          <div className="trace-outputs">{Array.from({length:Math.min(trace.output_rows,6)},(_,n) => <span key={n}>{String(trace.key ?? 'NULL')}{trace.order_amount !== null && trace.left_rows===1 && <> · <b>${trace.order_amount}</b></>}</span>)}{trace.output_rows === 0 && <span className="null-value">removed by INNER</span>}{trace.left_rows>1&&trace.order_amount!==null&&<small>Amounts vary across these left rows; total is shown at right.</small>}</div>
          {trace.contribution !== null && <div className="trace-contribution"><small>SUM CONTRIBUTION</small><strong>${trace.contribution}</strong>{trace.repeated && <span>full amount repeated</span>}</div>}
        </div>)}</div>
        {result.baseline_amount !== null && <div className="revenue-comparison"><div><small>BEFORE JOIN</small><strong>${result.baseline_amount}</strong></div><ArrowRight size={22}/><div><small>AFTER JOIN · SUM(order_amount)</small><strong className={result.fanout ? 'amber' : 'green'} data-testid="joined-revenue">${result.joined_amount}</strong></div><p>{result.fanout ? 'Summing after the join adds the repeated amounts too. Group the right side before attaching it.' : config.kind==='inner'&&result.unmatched_left_rows>0 ? `INNER removed ${result.unmatched_left_rows} unmatched left row(s), changing the amount included.` : config.aggregate_right ? 'Right-side aggregation made the join key unique. Amounts are attached once.' : 'Right-side keys are already unique on these matches. Each left amount is attached once.'}</p></div>}
      </section>
      <div className="two-column"><section className="card"><div className="card-title"><h3>Result rows</h3><span className="tag">{result.actual_rows} rows</span></div><Table rows={result.rows} repeatKey="left_order_id" caption="Joined result rows"/></section><section className="card"><div className="card-title"><h3>Prove your expectation</h3><ShieldCheck size={18}/></div><Proofs tests={result.tests}/><p className="muted small">NULL keys never match. {result.unmatched_left_rows} unmatched left rows; {result.null_left_keys} NULL left keys. Cardinality describes this fixture, not all possible future data.</p></section></div>
      {advanced && <SqlBlock sql={result.sql} />}
      <p className="footnote">{config.left_table==='order_items'?'Source item rows can share an order key with multiple payment attempts. Compare direct joining with aggregating the right side first.':'Left order inputs are prepared from the deterministic staging transformation.'} The right source, <code>{right.name}</code>, has {right.row_count} records. No warehouse is needed.</p>
    </>}
  </div>;
}

export function BuildLab({ scenario, staged, advanced, busy, build, lastRequest, execute, goStage }: {
  scenario: Scenario; staged: boolean; advanced: boolean; busy: boolean; build: BuildResult|null;
  lastRequest: BuildRequest|null; execute: (request: BuildRequest) => void; goStage: () => void;
}) {
  const [grain, setGrain] = useState(lastRequest?.grain ?? '');
  const [key, setKey] = useState(lastRequest?.primary_key[0] ?? '');
  const [sql, setSql] = useState(lastRequest?.sql ?? scenario.reference_sql.safe);
  const [strategy, setStrategy] = useState<'safe'|'fanout'>(lastRequest?.strategy ?? 'safe');
  function run(override?: 'safe'|'fanout') {
    const choice = override ?? strategy;
    const selectedSql = override ? scenario.reference_sql[choice] : sql;
    if (override) { setSql(selectedSql); setStrategy(choice); }
    execute({source_grain:'source_order_version', grain, primary_key:[key], strategy:choice, ...(advanced || override ? {sql:selectedSql} : {})});
  }
  const draftChanged = !!lastRequest && (grain !== lastRequest.grain || key !== lastRequest.primary_key[0] || (advanced && sql !== (lastRequest.sql ?? scenario.reference_sql[lastRequest.strategy])));
  return <div className="lab-view">
    <div className="section-heading"><div><span className="eyebrow">03 / MODEL & PROVE</span><h2>Build a fact you can explain.</h2><p>One completed order per row. Every assumption gets a test.</p></div><span className="tag"><ShieldCheck size={14}/> Invariant-based evaluation</span></div>
    {!staged && <div className="gate-card"><span className="gate-number">01</span><div><h3>Start by declaring the source grain.</h3><p>Raw orders contain multiple versions. Create staging before building your fact.</p><button className="primary-button" onClick={goStage}>Inspect source orders<ArrowRight size={16}/></button></div></div>}
    <div className="two-column build-columns"><section className="card"><div className="card-title"><div><span className="eyebrow">MODEL DEFINITION</span><h3><code>fct_orders</code></h3></div><StatusPill status={build?.evaluation.status ?? 'unknown'} label={build ? 'Last executed model' : 'Not built'}/></div>
      <p className="muted">Represent completed orders once, so downstream revenue can be added safely.</p>
      <label>What does one row represent?<select aria-label="Fact grain" value={grain} onChange={e => setGrain(e.target.value)}><option value="">Declare a grain…</option><option value="order">One completed order</option><option value="order_item">One order item</option><option value="customer">One customer</option></select></label>
      <label>What uniquely identifies that row?<select aria-label="Fact primary key" value={key} onChange={e => setKey(e.target.value)}><option value="">Choose a primary key…</option><option value="order_id">order_id</option><option value="customer_id">customer_id</option><option value="ordered_at">ordered_at</option></select></label>
      <div className="contract-note"><ShieldCheck size={17}/><p>Required contract: <strong>order</strong> grain, a unique non-null <code>order_id</code>, exact decimal amounts, UTC timestamps, and completed USD orders.</p></div>
      {advanced && <label>Transformation SQL<textarea className="sql-editor" aria-label="Fact SQL" spellCheck={false} value={sql} onChange={e => setSql(e.target.value)} rows={10}/><span className="field-hint">Known fixture tables + stg_orders + completed_orders. Equivalent SQL is welcome.</span></label>}
      <div className="button-row"><button className="primary-button" disabled={!staged || !grain || !key || busy} onClick={() => run()}><Play size={16}/>{busy ? 'Executing…' : 'Build & verify fact'}</button>{build && <button className={build.evaluation.status === 'pass' ? 'danger-button' : 'secondary-button'} disabled={busy || !grain || !key} onClick={() => run(build.evaluation.status === 'pass' ? 'fanout' : 'safe')}>{build.evaluation.status === 'pass' ? <GitMerge size={15}/> : <RotateCcw size={15}/>} {build.evaluation.status === 'pass' ? 'Break it: join items' : 'Repair: preserve order grain'}</button>}</div>
      {draftChanged && <p className="draft-note">Draft changed. The evidence shown is for the last executed model; build again to evaluate this draft.</p>}
    </section>
    <section className="card evidence-summary"><div className="card-title"><div><span className="eyebrow">THE PROOF</span><h3>Why is this model correct?</h3></div></div>
      {build ? <><StatusPill status={build.evaluation.status} label={build.evaluation.status === 'pass' ? 'All model assertions pass' : 'Model assertions failed'}/><p className="evidence-explanation">{build.evaluation.explanation}</p><div className="mini-stat-row"><div><strong>{build.fact.row_count ?? '—'}</strong><small>fact rows</small></div><div><strong>{build.evaluation.primary_key.unique ? 'Unique' : 'Not proven'}</strong><small>{build.fact.primary_key.join(' + ') || 'declared key'}</small></div><div><strong>{build.metric.value === null ? '—' : `$${build.metric.value}`}</strong><small>gross revenue</small></div></div><Proofs tests={build.evaluation.tests}/>{build.evaluation.warnings.map(w => <p key={w} className="warning-note"><TriangleAlert size={16}/>{w}</p>)}<p className="footnote">Explanation generated from deterministic execution and assertions.</p></> : <div className="empty-proof"><ShieldCheck size={38}/><h4>Correct SQL is the beginning.</h4><p>Build the model to check its schema, key, grain, business rules, and complete output against golden rows.</p></div>}
    </section></div>
    {build && <section className="card"><div className="card-title"><h3>Executed fact output</h3><span className="tag">Expected 3 completed orders</span></div><Table rows={build.fact.rows} columns={build.fact.columns} repeatKey="order_id" caption="Executed fact output"/>{advanced && build.fact.sql && <SqlBlock sql={build.fact.sql}/>}</section>}
  </div>;
}

export function MetricLab({ scenario, build, metric, busy, calculate, goBuild }: { scenario: Scenario; build: BuildResult|null; metric: Metric|null; busy: boolean; calculate: (name:string, aggregation:Metric['aggregation']) => void; goBuild: () => void }) {
  const [name, setName] = useState(metric?.name ?? 'Revenue');
  const [aggregation, setAggregation] = useState<Metric['aggregation']>(metric?.aggregation ?? 'SUM');
  const definition = metric ?? scenario.planned_metric;
  return <div className="lab-view">
    <div className="section-heading"><div><span className="eyebrow">04 / DEFINE THE BUSINESS MEANING</span><h2>A number needs a definition.</h2><p>The physical model stores orders. The semantic metric says what revenue means.</p></div><span className="tag"><Code2 size={14}/> Inspectable metric</span></div>
    <div className="metric-story"><span><code>fct_orders</code><small>Physical model</small></span><ArrowRight size={24}/><span><strong>Revenue</strong><small>Semantic definition</small></span><ArrowRight size={24}/><span><strong>Business answer</strong><small>Gross completed-order revenue</small></span></div>
    {!build && <div className="gate-card"><span className="gate-number">03</span><div><h3>Build the order fact first.</h3><p>A metric needs executable data behind its definition.</p><button className="primary-button" onClick={goBuild}>Build the fact<ArrowRight size={16}/></button></div></div>}
    {build && build.evaluation.status !== 'pass' && <div className="warning-note"><TriangleAlert size={19}/><span>The fact has failed assertions. You can calculate to observe the consequence; a matching metric value alone does not prove the model correct.</span></div>}
    <div className="two-column metric-columns"><section className="card"><div className="card-title"><h3>Define your Revenue metric</h3><span className="tag">Finance · USD</span></div><label>Display name<input aria-label="Metric name" maxLength={80} value={name} onChange={e => setName(e.target.value)}/></label><label>Aggregation<select aria-label="Metric aggregation" value={aggregation} onChange={e => setAggregation(e.target.value as Metric['aggregation'])}><option value="SUM">SUM · total order amounts</option><option value="AVG">AVG · average order amount</option><option value="COUNT">COUNT · non-null amounts</option></select></label>
      <dl className="metric-definition"><div><dt>Measure</dt><dd><code>order_amount</code></dd></div><div><dt>Time dimension</dt><dd><code>ordered_at</code> · UTC event time</dd></div><div><dt>Filters</dt><dd><code>status = 'completed'</code></dd></div><div><dt>Dimensions</dt><dd><code>customer_id</code>, <code>currency</code></dd></div><div><dt>Required grain</dt><dd>One row / completed order</dd></div><div><dt>Owner</dt><dd>Finance</dd></div></dl>
      <button className="primary-button" disabled={!build?.evaluation.sql_valid || !name.trim() || busy} onClick={() => calculate(name.trim(),aggregation)}><Play size={16}/>{busy ? 'Calculating…' : 'Calculate metric'}</button>
      {metric && (metric.name !== name || metric.aggregation !== aggregation) && <p className="draft-note">Definition changed. Calculate again; the result shown uses the last executed definition.</p>}
    </section><section className="card metric-answer"><span className="eyebrow">THE BUSINESS ANSWER</span><h3>{metric?.name ?? 'Revenue'}</h3><div className="metric-value" data-testid="metric-value">{metric?.value == null ? '—' : metric.aggregation === 'COUNT' ? `${Number(metric.value)} amounts` : `$${metric.value}`}</div><StatusPill status={metric?.status ?? 'unknown'} label={metric ? metric.status === 'pass' ? 'Matches expected metric' : 'Does not match Revenue definition' : 'Not calculated'}/><p>{metric?.evidence ?? 'The golden fixture totals $225.00. Define and calculate the metric to compare its value.'}</p><div className="business-definition"><span className="eyebrow">WHAT THIS NUMBER MEANS</span><p>{definition.description}</p></div><p className="footnote">Three completed orders: $100 + $50 + $75 = $225. A $25 return is present; net revenue is a separate definition.</p></section></div>
  </div>;
}
