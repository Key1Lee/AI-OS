import { useEffect, useRef, useState } from 'react';
import { api, download } from './api';
import { Badge, Code, Icon, Panel } from './components';
import { Builder, CompatibilityLab, ContractView, Family, TestTypes } from './labs';
import type { Bundle, Preview, Result, Rule, Scenario, Status } from './types';

const scenarioId = 'commerce-current-orders-v1';
const navigation = [
  {id: 'lab', title: 'Quality gates', icon: 'gates', group: 'PRACTICE'},
  {id: 'contract', title: 'Data contract', icon: 'contract'},
  {id: 'builder', title: 'Rule builder', icon: 'builder'},
  {id: 'compatibility', title: 'Contract evolution', icon: 'evolution', group: 'UNDERSTAND'},
  {id: 'tests', title: 'Unit vs data tests', icon: 'tests'},
  {id: 'family', title: 'System family', icon: 'family', group: 'CONNECT'},
];
const levels = [
  {name: 'Schema', dimensions: ['schema'], question: 'Did the producer keep its column promises?'},
  {name: 'Row', dimensions: ['completeness', 'validity'], question: 'Are individual values usable?'},
  {name: 'Key / relationship', dimensions: ['uniqueness', 'referential_integrity'], question: 'Does each order occur once, with a real customer?'},
  {name: 'Dataset', dimensions: ['freshness', 'volume'], question: 'Did enough data arrive recently?'},
  {name: 'Business', dimensions: ['business_rule', 'consistency', 'reconciliation'], question: 'Do the rows obey the business agreement?'},
];

function worst(results: Result[]): Status {
  return results.some(r => r.status === 'FAIL') ? 'FAIL' : results.some(r => r.status === 'UNKNOWN') || !results.length ? 'UNKNOWN' : results.some(r => r.status === 'WARN') ? 'WARN' : 'PASS';
}
function shortClock(value: string) { return new Intl.DateTimeFormat('en-GB', {timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit'}).format(new Date(value)); }

export default function App() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [view, setView] = useState('lab');
  const [corruptions, setCorruptions] = useState<string[]>([]);
  const [customRules, setCustomRules] = useState<Rule[]>([]);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('contract_grain');
  const [prediction, setPrediction] = useState<Status>('PASS');
  const [submittedPrediction, setSubmittedPrediction] = useState<Status | null>(null);
  const [stage, setStage] = useState(1);
  const [advanced, setAdvanced] = useState(false);
  const run = useRef(0);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    api<Scenario>(`/api/scenarios/${scenarioId}`, undefined, controller.signal).then(value => {setScenario(value);setPreview({datasets:value.datasets,executed_at:value.clock});}).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, []);
  function invalidate() { generation.current++; setBundle(null); setSubmittedPrediction(null); setError(''); }
  async function changeData(next: string[]) {
    invalidate(); setCorruptions(next); setPreviewing(true);
    const requestGeneration = generation.current;
    try {
      const value = await api<Preview>(`/api/scenarios/${scenarioId}/preview`, {corruptions:next});
      if (generation.current === requestGeneration) setPreview(value);
    } catch (e) { if (generation.current === requestGeneration) setError((e as Error).message); }
    finally { if (generation.current === requestGeneration) setPreviewing(false); }
  }
  async function runChecks() {
    setBusy(true); setError(''); const requestGeneration = generation.current;
    try {
      const value = await api<Bundle>(`/api/scenarios/${scenarioId}/validate`, {corruptions,additional_rules:customRules,run_id:`learning-${++run.current}`});
      if (generation.current === requestGeneration) { setBundle(value); setSubmittedPrediction(prediction); }
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  function reset() { setCustomRules([]); setSelected('contract_grain'); setStage(1); void changeData([]); }
  if (!scenario || !preview) return <div className="loading"><div className="brand-mark">Q</div><h1>Data Quality & Contracts</h1><p>{error || 'Loading the deterministic commerce fixture…'}</p></div>;
  const rules = [...scenario.rules, ...customRules];
  const rule = rules.find(r => r.id === selected) || rules[0];
  const result = bundle?.results.find(r => r.rule_id === rule.id);
  const rows = preview.datasets.fct_orders.rows || [];
  const affected = new Set(result?.evidence.sample_rows.map(row => row._row_number) || []);
  const gateOpen = bundle?.gate.status === 'OPEN';
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><Icon name="gates" /></span><span>Quality &<br/>Contracts</span></div>
      <div className="project-pill"><span className="tiny-dot" /> COMMERCE LAB <span>01</span></div>
      <nav aria-label="Main navigation">{navigation.map(item => <div key={item.id}>{item.group && <p className="nav-group">{item.group}</p>}<button aria-label={item.title} disabled={busy || previewing} className={`nav-item ${view === item.id ? 'active' : ''}`} onClick={() => {setView(item.id);setError('');}} aria-current={view === item.id ? 'page' : undefined}><Icon name={item.icon}/>{item.title}{view === item.id && <span className="nav-arrow">↗</span>}</button></div>)}</nav>
      <div className="sidebar-note"><span className="eyebrow">THE QUESTION TO ASK</span><p>Did the data still satisfy the assumptions our business depends on?</p><div className="local-badge"><span className="tiny-dot" /> LOCAL · DETERMINISTIC</div></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="breadcrumbs">Data systems <span>/</span> <strong>Quality & Contracts</strong></div><div className="top-actions"><span className="clock">◷ {shortClock(preview.executed_at)} KST <small>SIMULATED</small></span><button className="icon-button" onClick={reset} disabled={busy || previewing} title="Reset lab" aria-label="Reset lab"><Icon name="reset" /></button><button className="button quiet" disabled={!bundle || busy || previewing} onClick={() => download('quality-evidence.json', {scenario_id:scenario.id, ...bundle,datasets:preview.datasets})}><Icon name="export"/>Export evidence</button></div></header>
      <main>
        {error && <div className="error" role="alert">{error}</div>}
        {view === 'lab' && <>
          <div className="page-intro"><div><p className="eyebrow">EXPERIMENT 01 / TRUSTED ORDERS</p><h1>A table exists.<br/><span>Can we trust it?</span></h1><p className="intro-copy">Make a promise. Check the data. Decide what can pass.</p></div><div className="lesson-tag"><span>01</span><div>SEE → BREAK → REPAIR<small>10 orders. Real evidence.</small></div></div></div>
          <div className="promise-bar"><span className="promise-icon"><Icon name="contract" /></span><div><span className="eyebrow">THE DATA CONTRACT</span><strong>fct_orders <span>promises</span> 1 row / current order</strong></div><span className="mono key-pill">PK · order_id</span><button className="text-button" onClick={() => setView('contract')}>Inspect contract ↗</button></div>
          <section className="flow-panel" aria-label="Quality flow">
            <div className="flow-heading"><span className="eyebrow">DATA → VALIDATION → PUBLICATION</span><span className="context-note">Upstream stages are authored context</span></div>
            <div className="quality-flow">{scenario.flow.map((node, i) => <div className="flow-unit" key={node}><div className={`flow-node ${i === 3 ? (bundle ? gateOpen ? 'node-pass' : 'node-fail' : 'node-unknown') : i === 4 ? gateOpen ? 'node-pass' : 'node-withheld' : ''}`}><span className="node-step">{['SOURCE', 'STAGING', 'INTERMEDIATE', 'VALIDATED FACT', 'DOWNSTREAM MART'][i]}</span><strong className="mono">{node}</strong><span className="node-status">{i < 3 ? 'CONTEXT' : i === 3 ? bundle ? gateOpen ? 'CHECKED' : 'CHECKS FAILED' : 'NOT CHECKED' : gateOpen ? 'ELIGIBLE TO PUBLISH' : 'WITHHELD'}</span></div>{i < 4 && <span className={`flow-arrow ${i === 3 && !gateOpen ? 'blocked-arrow' : ''}`} aria-hidden="true">{i === 3 && !gateOpen ? '⊣' : '→'}</span>}</div>)}</div>
            <div className={`gate-strip ${bundle ? gateOpen ? 'gate-open' : 'gate-blocked' : 'gate-pending'}`} aria-live="polite"><span className="gate-symbol">{bundle ? gateOpen ? '✓' : '×' : '—'}</span><div><strong>{bundle ? gateOpen ? 'Quality gate open' : 'Quality gate blocked' : 'The gate is waiting for evidence'}</strong><span>{bundle ? gateOpen ? bundle.summary.WARN ? 'Nonblocking warnings remain. All blocking checks pass.' : 'All blocking assumptions pass. Publication is eligible.' : `${bundle.gate.blocking_rule_ids.length} blocking checks need attention. The mart is not published.` : 'The fact table has rows. Run its checks before treating it as trusted.'}</span></div><span className="gate-label">{bundle ? bundle.gate.publication : 'WITHHELD'}</span></div>
          </section>
          <div className="experiment-toolbar"><div className="prediction"><label htmlFor="prediction">Predict the selected check</label><select id="prediction" value={prediction} onChange={e => setPrediction(e.target.value as Status)}>{['PASS','WARN','FAIL','UNKNOWN'].map(value => <option key={value}>{value}</option>)}</select></div><button className="button primary" onClick={runChecks} disabled={busy || previewing}><Icon name="play"/>{busy ? 'Checking…' : 'Run validation'}</button><div className="summary" aria-label="Validation summary">{(['PASS','WARN','FAIL','UNKNOWN'] as Status[]).map(status => <span key={status} className={`summary-item ${status.toLowerCase()}`}><strong>{bundle ? bundle.summary[status] : '—'}</strong>{status}</span>)}</div></div>
          <div className="lab-grid">
            <section className="panel checks-panel"><div className="panel-heading split"><div><p className="eyebrow">FIVE LEVELS OF QUALITY</p><h2>What are we checking?</h2></div><span className="count">{rules.length} checks</span></div>
              {levels.map((level,i) => { const categoryRules = rules.filter(r => level.dimensions.includes(r.dimension)); const categoryResults = bundle?.results.filter(r => categoryRules.some(rule => rule.id === r.rule_id)) || []; return <div className="check-level" key={level.name}><div className="level-heading"><span className="level-number">{i+1}</span><strong>{level.name}</strong>{bundle && <Badge status={worst(categoryResults)}/>}</div><p>{level.question}</p>{categoryRules.map(item => { const found = bundle?.results.find(r => r.rule_id === item.id);return <button key={item.id} className={`rule-row ${rule.id === item.id ? 'selected' : ''}`} aria-label={item.name} disabled={busy || previewing} onClick={() => {setSelected(item.id);setSubmittedPrediction(null);}} aria-pressed={rule.id === item.id}><span>{item.name}</span>{found ? <span className={`result-dot ${found.status.toLowerCase()}`} title={found.status} aria-label={found.status}>{found.status === 'PASS' ? '✓' : found.status === 'FAIL' ? '×' : found.status === 'WARN' ? '!' : '—'}</span> : <span className="result-dot unknown" aria-label="Not run">—</span>}</button>;})}</div>;})}
            </section>
            <div className="evidence-column">
              <section className="panel evidence-panel"><div className="panel-heading split"><div><p className="eyebrow">SELECTED EXPECTATION</p><h2>{rule.name}</h2></div><Badge status={result?.status || 'UNKNOWN'}>{result?.status || 'NOT RUN'}</Badge></div>
                <div className="purpose"><span className="eyebrow">WHY DOES THIS TEST EXIST?</span><p>{rule.description}</p></div><div className="comparison"><div><span className="eyebrow">EXPECTED</span><strong>{rule.expectation.kind === 'unique' ? 'Rows = distinct keys' : rule.expectation.kind === 'not_null' ? `Completeness ≥ ${Number(rule.expectation.minimum_rate)*100}%` : rule.expectation.kind === 'freshness' ? `Age ≤ ${rule.expectation.maximum_age_minutes} min` : rule.expectation.kind === 'relationship' ? 'Every applicable key has a parent' : rule.expectation.kind === 'schema' ? 'Required schema + valid values' : rule.expectation.kind === 'reconciliation' ? 'Totals within declared tolerance' : rule.expectation.kind === 'volume' ? `${rule.expectation.minimum}–${rule.expectation.maximum} rows` : 'Documented expectation holds'}</strong></div><span className="comparison-arrow">→</span><div><span className="eyebrow">OBSERVED</span><strong>{!result ? 'Awaiting validation' : rule.expectation.kind === 'unique' ? `${result.evidence.metrics.rows} rows / ${result.evidence.metrics.distinct_non_null_keys} IDs` : result.failed_rows === null ? result.status === 'UNKNOWN' ? 'Evidence unavailable' : result.status : `${result.failed_rows} affected rows`}</strong></div></div>
                {result && <div className="fact-evidence"><span className="fact-label">FACT · DETERMINISTIC EVIDENCE</span><p>{result.evidence.message}</p></div>}
                {result && submittedPrediction && <p className="prediction-result">You predicted <strong>{submittedPrediction}</strong>. This check returned <strong>{result.status}</strong>. Compare the evidence above.</p>}
                <div className="policy-line"><span>Severity <strong>{rule.severity}</strong></span><span>{rule.blocking ? '● Blocks publication on breach or unknown' : '○ Nonblocking · pipeline may continue'}</span></div>
                <button className="text-button" onClick={() => setAdvanced(!advanced)} aria-expanded={advanced}>{advanced ? 'Hide' : 'Show'} rule & evidence JSON {advanced ? '↑' : '↓'}</button>{advanced && <Code value={{rule,result:result || 'No evidence yet'}}/>}
              </section>
              <section className="panel break-panel"><div className="panel-heading split"><div><p className="eyebrow">CONTROLLED CORRUPTION</p><h2>Break it. See what changes.</h2></div><span className="break-mark">↯</span></div><p className="muted">Choose one or combine failures. Every data change clears old validation.</p><div className="break-options">{Object.entries(scenario.corruptions).map(([id, item],i) => <button key={id} disabled={busy || previewing} className={`break-option ${corruptions.includes(id) ? 'chosen' : ''}`} onClick={() => void changeData(corruptions.includes(id) ? corruptions.filter(x => x !== id) : [...corruptions,id])} aria-pressed={corruptions.includes(id)}><span>{String(i+1).padStart(2,'0')}</span>{item.title}<b>{corruptions.includes(id) ? '✓' : '+'}</b></button>)}</div>
                {corruptions.length > 0 && <div className="cause-effect">{corruptions.map(id => <div key={id}><span className="eyebrow">CAUSE → EXAMPLE CONSEQUENCE · IN ISOLATION</span><p>{scenario.corruptions[id].cause}</p><strong>↓</strong><p>{scenario.corruptions[id].consequence}</p></div>)}<button className="button repair" onClick={() => void changeData([])} disabled={busy || previewing}>Fix fixture & verify again ↗</button></div>}
              </section>
              <section className="panel coach"><p className="eyebrow">LEARNING PATH · {stage} / 7</p><h2>{scenario.learning_levels[stage-1]}</h2><p>{['NULL is a missing value. Uniqueness prevents repeated identifiers. Allowed values give categories a shared meaning.','Modeling declares row meaning. Quality checks its keys, schema and parent references. A unique key alone cannot prove semantic grain.','Simple null checks can pass while totals disagree. Open reconciliation and compare the captured, refunded and warehouse totals.','A task can succeed with stale or empty data. Inspect arrival age and row volume; the gate controls whether publication is eligible.','A contract says what must remain true. A test says how we verify it. Open Contract evolution to challenge a new version.','Modeling declares. Orchestration executes. Quality verifies. Observability investigates. Toptal assesses. Explore System family.','Finance suspects inflation. Duplicate an order, predict the key result, inspect the actual repeated rows and totals, then repair and verify. No score is awarded here.'][stage-1]}</p><div className="learning-dots" aria-label={`Learning stage ${stage} of 7`}>{scenario.learning_levels.map((_,i) => <span key={i} className={i+1<=stage ? 'unlocked' : ''}/>)}</div>{stage<7 && <button className="text-button" onClick={() => setStage(stage+1)}>Explore next concept →</button>}</section>
            </div>
          </div>
          <section className="panel data-panel"><div className="panel-heading split"><div><p className="eyebrow">OBSERVED FIXTURE · NOT A VALIDATION BY ITSELF</p><h2>Look at the actual rows</h2></div><span className="count">{rows.length} rows{result?.evidence.sample_rows.length ? ' · evidence highlighted' : ''}</span></div><div className="table-scroll"><table><thead><tr><th>ROW</th>{['order_id','customer_id','status','payment_status','net_revenue','ordered_at'].map(c=><th className="mono" key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i} className={affected.has(i+1) ? 'affected' : ''}><td>{i+1}</td>{['order_id','customer_id','status','payment_status','net_revenue','ordered_at'].map(c=><td key={c} className={c==='order_id'||c==='customer_id' ? 'mono' : ''}>{row[c]===undefined ? <span className="missing">COLUMN MISSING</span> : row[c]===null ? <span className="missing">NULL</span> : String(row[c])}</td>)}</tr>)}</tbody></table>{rows.length===0 && <p className="empty-note">No rows. Run validation to inspect volume and UNKNOWN row checks.</p>}</div>{result?.evidence.sample_rows.length ? <p className="table-footnote">Highlights are the first {result.evidence.sample_rows.length} evidence rows for the selected check; at most 8 are displayed. Full rows are in the export.</p> : <p className="table-footnote">The fixture contains source concepts and a prebuilt fact. This app validates the fact; it does not transform the source tables.</p>}</section>
        </>}
        {view === 'contract' && <ContractView scenario={scenario}/>}
        {view === 'builder' && <Builder scenario={scenario} rules={customRules} onAdd={newRule => {invalidate();setCustomRules([...customRules,newRule]);setSelected(newRule.id);setView('lab');}} onRemove={id=>{invalidate();setCustomRules(customRules.filter(r=>r.id!==id));}}/>}
        {view === 'compatibility' && <CompatibilityLab scenario={scenario} onError={setError}/>}
        {view === 'tests' && <TestTypes/>}
        {view === 'family' && <Family scenario={scenario} bundle={bundle}/>}
        <footer><span>DEFINED → TESTED → ENFORCED → OBSERVED</span><span>Quality establishes the failure. Observability investigates its cause.</span></footer>
      </main>
    </div>
  </div>;
}
