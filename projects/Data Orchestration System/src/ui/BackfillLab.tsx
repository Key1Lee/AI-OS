import { useMemo, useState } from 'react';
import { clockLabel, ecommerceWorkflow, EXAMPLE_PARTITIONS, planBackfill, simulateBackfill, TODAY } from '../engine';
import type { BackfillResult, PartitionRecord } from '../engine';
import { Icon, StateBadge } from './components';

export function BackfillLab({ onResultChange }: { onResultChange: (result: BackfillResult | null) => void }) {
  const [records, setRecords] = useState<PartitionRecord[]>(structuredClone(EXAMPLE_PARTITIONS));
  const [start, setStart] = useState('2026-09-27'), [end, setEnd] = useState('2026-09-29');
  const [mode, setMode] = useState<'missing' | 'replace'>('missing');
  const [workers, setWorkers] = useState(2), [parallel, setParallel] = useState(2), [fail, setFail] = useState(false);
  const [result, setResult] = useState<BackfillResult | null>(null), [error, setError] = useState('');
  const [selected, setSelected] = useState('2026-09-28');
  const preview = useMemo(() => { try { return { plan: planBackfill(start, end, TODAY, records, mode), error: '' }; } catch (e) { return { plan: null, error: (e as Error).message }; } }, [start, end, records, mode]);
  const invalidate = () => { setResult(null); onResultChange(null); setError(''); };
  function run() {
    if (!preview.plan) return;
    try {
      const failedDate = preview.plan.items.find(i => i.partition === '2026-09-28' && i.action === 'RUN')?.partition;
      if (fail && !failedDate) throw new Error('Include Sep 28 as a partition to run before injecting its failure.');
      const next = simulateBackfill(ecommerceWorkflow(), preview.plan, { execution_id: crypto.randomUUID(), workers, partition_concurrency: parallel, fail_partition: fail ? failedDate : undefined });
      setResult(next); onResultChange(next); setError('');
      setRecords(previous => [...previous.filter(r => !next.partitions.some(n => n.partition === r.partition)), ...next.partitions].sort((a, b) => a.partition.localeCompare(b.partition)));
    } catch (e) { setError((e as Error).message); }
  }
  const selectedRun = result?.runs.find(r => r.partition === selected);
  return <div className="backfill-lab">
    <section className="panel"><div className="panel-heading"><div><span className="eyebrow">BACKFILL LAB</span><h2>Give missing days their own run.</h2></div><span className="label"><Icon name="calendar" size={14}/> Today · Oct 2, 2026</span></div>
      <p className="muted">A partition is one date’s slice of data. A backfill runs today to process historical partitions. Sep 27–29 are missing; Sep 30–Oct 2 already exist.</p>
      <div className="backfill-controls"><label>From<input aria-label="Backfill start" type="date" value={start} max="2026-10-01" onChange={e => { setStart(e.target.value); invalidate(); }}/></label><span className="date-arrow"><Icon name="arrow"/></span><label>Through<input aria-label="Backfill end" type="date" value={end} max="2026-10-01" onChange={e => { setEnd(e.target.value); invalidate(); }}/></label>
        <label>Existing successful runs<select aria-label="Existing partition policy" value={mode} onChange={e => { setMode(e.target.value as 'missing' | 'replace'); invalidate(); }}><option value="missing">Keep existing output</option><option value="replace">Reprocess successful dates</option></select></label>
        <label>Shared workers<select aria-label="Backfill workers" value={workers} onChange={e => { setWorkers(Number(e.target.value)); invalidate(); }}>{[1, 2, 3, 4].map(n => <option key={n}>{n}</option>)}</select></label>
        <label>Concurrent partitions<select aria-label="Partition concurrency" value={parallel} onChange={e => { setParallel(Number(e.target.value)); invalidate(); }}>{[1, 2, 3].map(n => <option key={n}>{n}</option>)}</select></label>
      </div>
      <div className="backfill-actions"><label className="checkbox"><input type="checkbox" checked={fail} onChange={e => { setFail(e.target.checked); invalidate(); }}/>Fail Sep 28 only</label><div><button className="button quiet" onClick={() => { setRecords(structuredClone(EXAMPLE_PARTITIONS)); invalidate(); }}>Reset partitions</button><button className="button primary" onClick={run} disabled={!preview.plan}><Icon name="play" size={15}/>Run backfill</button></div></div>
      {(preview.error || error) && <p role="alert" className="form-error">{error || preview.error}</p>}
      <div className="partition-grid" aria-label="Partition calendar">{records.map(record => {
        const item = preview.plan?.items.find(i => i.partition === record.partition);
        return <button key={record.partition} data-testid={`partition-${record.partition}`} className={`partition-card ${item ? 'targeted' : ''} ${selected === record.partition ? 'chosen' : ''}`} onClick={() => setSelected(record.partition)}>
          <span>{new Intl.DateTimeFormat('en-US', { month: 'short', timeZone: 'UTC' }).format(new Date(`${record.partition}T00:00:00Z`)).toUpperCase()} {record.partition.slice(0, 4)}</span><strong>{record.partition.slice(-2)}</strong>
          <span className={`partition-status ${record.status.toLowerCase()}`}>{record.status === 'MISSING' ? '○ MISSING' : record.status === 'FAILED' ? '× FAILED' : '✓ SUCCESS'}</span>
          <small>{item?.action === 'RUN' ? 'Targeted for replay' : item?.action === 'SKIP' ? 'Keep existing' : record.partition === TODAY ? 'Current partition' : 'Outside range'}</small>
          <small>{record.rows === null ? 'No published rows' : `${record.rows} published rows`}</small>
        </button>;
      })}</div>
      {!result && preview.plan && <div className="backfill-plan"><strong>Preview · {preview.plan.items.filter(i => i.action === 'RUN').length} to run · {preview.plan.items.filter(i => i.action === 'SKIP').length} to keep</strong><span>No execution has started. Each targeted partition follows the full dependency graph.</span></div>}
      {result && <div className="backfill-result" data-testid="backfill-result"><Icon name="check"/><div><strong>{result.partitions.filter(p => p.status === 'SUCCESS').length} successful · {result.partitions.filter(p => p.status === 'FAILED').length} failed · {result.runs.length} runs</strong><span>{result.total_minutes} virtual minutes · peak {result.peak_workers}/{workers} shared workers · peak {result.peak_partitions}/{parallel} concurrent partitions</span></div></div>}
      {selectedRun && <div className="partition-evidence"><div><strong>Partition {selected}</strong><StateBadge status={selectedRun.status}/></div><p>Executed on {TODAY}, {selectedRun.start_time?.slice(11, 16)}–{clockLabel(selectedRun.now)} Asia/Seoul. Historical data date, today’s execution time.</p><div className="partition-task-states">{Object.values(selectedRun.tasks).map(t => <span key={t.task_id}><code>{t.task_id}</code><StateBadge status={t.status}/></span>)}</div></div>}
      <p className="small muted">This example’s tasks replace each partition with the same authored 100-row payload: 100 → 100 on reprocessing. Actual transformation and incremental write semantics belong to the Modeling System.</p>
    </section>
    <section className="panel late-data"><div className="late-data-icon"><Icon name="clock" size={26}/></div><div><span className="eyebrow">LATE-ARRIVING DATA</span><h2>The event date is not the arrival date.</h2><p>An order happened on <strong>Sep 28</strong> but arrived on <strong>Oct 1</strong>. A one-day lookback misses it; a three-day lookback can include it. Or target Sep 28 with a backfill. Modeling decides which rows change; orchestration decides when that partition is reprocessed.</p><button className="text-button" onClick={() => { setStart('2026-09-28'); setEnd('2026-09-28'); setMode('replace'); invalidate(); }}>Target Sep 28 <Icon name="arrow" size={15}/></button></div></section>
  </div>;
}
