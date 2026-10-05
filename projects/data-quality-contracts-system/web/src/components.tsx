import type { ReactNode } from 'react';
import type { Status } from './types';
export function Badge({status, children}: {status: Status; children?: ReactNode}) {
  return <span className={`badge ${status.toLowerCase()}`}><span aria-hidden="true">{status === 'PASS' ? '✓' : status === 'WARN' ? '!' : status === 'FAIL' ? '×' : '—'}</span>{children || status}</span>;
}
export function Icon({name}: {name: string}) {
  const paths: Record<string,string> = {
    gates: 'M4 3h6v6H4z M14 3h6v6h-6z M4 15h6v6H4z M14 15h6v6h-6z M7 9v6 M17 9v6',
    contract: 'M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h5',
    builder: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
    evolution: 'M4 7h13 M13 3l4 4-4 4 M20 17H7 M11 13l-4 4 4 4',
    tests: 'M9 3h6 M10 3v7l-5 8q-1 3 2 3h10q3 0 2-3l-5-8V3 M8 15h8',
    family: 'M12 3v5 M4 12h16 M4 12v6 M12 12v6 M20 12v6 M9 8h6v4H9z',
    play: 'M8 4l12 8-12 8z', reset: 'M5 7a8 8 0 1 1-1 8 M5 3v5H1', export: 'M12 3v13 M7 11l5 5 5-5 M4 17v4h16v-4',
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{<path d={paths[name] || paths.gates} />}</svg>;
}
export function Code({value}: {value: unknown}) { return <pre className="code">{typeof value === 'string' ? value : JSON.stringify(value, null, 2)}</pre>; }
export function Panel({title, eyebrow, children}: {title: string; eyebrow?: string; children: ReactNode}) {
  return <section className="panel"><div className="panel-heading">{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{children}</section>;
}
