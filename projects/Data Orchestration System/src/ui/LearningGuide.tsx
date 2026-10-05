import { Icon } from './components';

const CONCEPTS = [
  ['Workflow', 'One coordinated set of tasks that produces an outcome.', 'Extract → stage → transform → publish → refresh'],
  ['Task', 'One unit of work, with inputs, outputs, duration, and an execution state.', 'build_fct_orders → produces the asset fct_orders'],
  ['Dependency', 'A rule about what must finish before another task can run.', 'stg_orders = SUCCESS AND stg_customers = SUCCESS → int_orders'],
  ['Blocked', 'An upstream result prevents this task from starting. A blocked task did not execute and fail.', 'extract_customers FAILED → int_orders BLOCKED'],
  ['Retry', 'Another attempt after a temporary error. Retry delays release the worker. A deterministic error needs a fix.', 'API timeout → wait 5 min → attempt 2'],
  ['Idempotency', 'Given the same inputs, rerunning generally produces the same correct state.', 'Replace: 100 → 100 rows. Append the same payload: 100 → 200 rows.'],
  ['Schedule', 'A time rule makes a workflow eligible. Dependencies and capacity still decide which tasks can start.', 'Daily 06:00 Asia/Seoul → eligible, not all tasks ready'],
  ['Data-driven execution', 'A declared asset update can trigger the workflow instead of a clock time.', 'Orders source updated → workflow starts → dependencies still apply'],
  ['Partition', 'One slice of data identified by a key, such as an event date.', 'fct_orders[Sep 28] is separate from fct_orders[Sep 29]'],
  ['Backfill', 'Run today to reprocess a bounded range of historical partitions.', 'Today Oct 2 → replay Sep 27, Sep 28, Sep 29'],
  ['Concurrency', 'A shared worker budget limits simultaneous work, even when more tasks are ready.', '2 workers → 2 tasks running; other ready tasks wait'],
  ['Critical path', 'The longest duration-weighted dependency chain gives a lower bound on completion time.', 'A 2m → B 8m → D 5m = 15m; speeding up parallel C 2m may not help'],
  ['Execution → observability', 'The simulator emits facts: what ran, when, which attempt, and what error. Observability consumes those facts to investigate.', 'ExecutionEvent → Observability; scenario + evidence → Toptal'],
];
export function LearningGuide() {
  return <section className="panel learning-guide"><div className="panel-heading"><div><span className="eyebrow">A SMALL VOCABULARY</span><h2>Understand the run before the syntax.</h2></div><Icon name="book" size={26}/></div><p className="muted">Follow the loop: see → predict → run → observe → explain → break → rerun. These concepts use the same facts in beginner and advanced mode.</p><div className="concept-grid">{CONCEPTS.map(([title, explanation, example], i) => <article key={title}><span className="concept-number">{String(i + 1).padStart(2, '0')}</span><h3>{title}</h3><p>{explanation}</p><div>{example}</div></article>)}</div></section>;
}
