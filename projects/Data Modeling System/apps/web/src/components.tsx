import { ArrowRight, Check, CircleCheck, CircleHelp, Code2, KeyRound, TriangleAlert, X } from 'lucide-react';
import type { Column, Model, Row, Status, Step, TestResult } from './types';

const statusLabels: Record<Status, string> = { pass: 'Valid', warning: 'Warning', fail: 'Invalid', unknown: 'Unknown' };
export function StatusPill({ status, label }: { status: Status; label?: string }) {
  const Icon = status === 'pass' ? CircleCheck : status === 'unknown' ? CircleHelp : TriangleAlert;
  return <span className={`status-pill ${status}`}><Icon size={13} aria-hidden="true" />{label ?? statusLabels[status]}</span>;
}

export function Table({ rows, columns, repeatKey, caption }: { rows: Row[]; columns?: Column[]; repeatKey?: string; caption: string }) {
  const names = columns?.map(c => c.name) ?? Object.keys(rows[0] ?? {});
  const counts = new Map<unknown, number>();
  if (repeatKey) rows.forEach(r => counts.set(r[repeatKey], (counts.get(r[repeatKey]) ?? 0) + 1));
  return <div className="table-scroll" tabIndex={0} aria-label={`${caption}, scrollable table`}>
    <table><caption className="sr-only">{caption}</caption>
      <thead><tr>{names.map(name => <th key={name}><span>{name}</span>{columns && <small>{columns.find(c => c.name === name)?.data_type.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMPTZ')}</small>}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i} className={repeatKey && (counts.get(row[repeatKey]) ?? 0) > 1 ? 'repeated-row' : ''}>
        {names.map(name => <td key={name}>{row[name] == null ? <span className="null-value">NULL</span> : typeof row[name] === 'object' ? JSON.stringify(row[name]) : String(row[name])}</td>)}
      </tr>)}</tbody>
    </table>
    {!rows.length && <p className="empty-table">No rows. Run the transformation to inspect its output.</p>}
  </div>;
}

export function Proofs({ tests }: { tests: TestResult[] }) {
  return <div className="proof-list">{tests.map(test => <details key={test.id} className={`proof ${test.status}`}>
    <summary><span className="proof-icon">{test.status === 'pass' ? <Check size={15} /> : <X size={15} />}</span><span>{test.name}</span><StatusPill status={test.status} label={test.status === 'pass' ? 'Pass' : 'Fail'} /></summary>
    <div className="proof-body"><p>{test.evidence}</p><div className="proof-values"><div><small>EXPECTED</small><pre>{JSON.stringify(test.expected, null, 2)}</pre></div><div><small>ACTUAL</small><pre>{JSON.stringify(test.actual, null, 2)}</pre></div></div></div>
  </details>)}</div>;
}

export function SqlBlock({ sql, label = 'Executed SQL' }: { sql: string; label?: string }) {
  return <div className="sql-block"><div className="sql-label"><Code2 size={14} /><span>{label}</span><span>DuckDB SQL</span></div><pre><code>{sql}</code></pre></div>;
}

export function StepDetails({ step, close }: { step: Step; close: () => void }) {
  const ran = step.output_rows !== null;
  return <section className="card step-detail" aria-label="Transformation difference">
    <div className="card-title"><div><span className="eyebrow">SHOW ME WHY</span><h3>{step.operation.toLowerCase().replaceAll('_', ' ')}</h3></div><button className="icon-button" aria-label="Close transformation details" onClick={close}><X size={18} /></button></div>
    <div className="before-after"><div><small>BEFORE</small><strong>{step.input_model}</strong><span>{step.input_grain}</span><b>{step.input_rows ?? '—'} <em>rows</em></b></div><ArrowRight size={24} /><div><small>AFTER</small><strong>{step.output_model}</strong><span>{step.output_grain}</span><b>{step.output_rows ?? '—'} <em>{ran ? 'rows' : 'not run'}</em></b></div></div>
    <p className="why-callout"><CircleHelp size={17} /><span><strong>Why this step exists</strong>{step.why}</span></p>
    <div className="diff-grid">{!!Object.keys(step.columns_renamed).length && <div><small>COLUMNS RENAMED</small>{Object.entries(step.columns_renamed).map(([a,b]) => <p key={a}><code>{a}</code><ArrowRight size={12}/><code>{b}</code></p>)}</div>}
      {!!step.columns_added.length && <div><small>COLUMNS ADDED</small><p>{step.columns_added.join(', ')}</p></div>}
      {!!step.columns_removed.length && <div><small>COLUMNS REMOVED</small><p>{step.columns_removed.join(', ')}</p></div>}
      {(['filters','joins','aggregations','windows'] as const).map(kind => step[kind].length ? <div key={kind}><small>{kind.toUpperCase()}</small>{step[kind].map((s,i) => <p key={i}><code>{s}</code></p>)}</div> : null)}
    </div>
    {step.tests.length > 0 && <Proofs tests={step.tests} />}
    {!ran && <p className="muted small">Planned transformation. Row counts and tests appear after execution.</p>}
  </section>;
}

export function ModelQuestions({ model }: { model: Model }) {
  return <dl className="model-questions">
    <div><dt>01 <span>Grain</span></dt><dd><StatusPill status={model.grain.status} label={model.grain.label} /><p>{model.grain.evidence}</p></dd></div>
    <div><dt>02 <span>Key</span></dt><dd className="key-list"><KeyRound size={15}/><code>{model.primary_key.length ? model.primary_key.join(' + ') : 'Not declared'}</code></dd></div>
    <div><dt>03 <span>Relationships</span></dt><dd>{model.parents.length ? model.parents.map(p => <code key={p} className="inline-code">{p}</code>) : model.layer === 'source' ? 'Operational source; explore its designed relationships below.' : 'No transformation has been executed.'}</dd></div>
    <div><dt>04 <span>Transformation</span></dt><dd>{model.why}</dd></div>
    <div><dt>05 <span>Proof</span></dt><dd>{model.tests.length ? <><strong>{model.tests.filter(t => t.status === 'pass').length} / {model.tests.length}</strong> assertions pass</> : 'Declare the grain, execute the model, then test its assumptions.'}</dd></div>
  </dl>;
}
