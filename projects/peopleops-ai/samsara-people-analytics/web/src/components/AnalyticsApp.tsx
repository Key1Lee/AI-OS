"use client";
import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DEPARTMENTS, YEARS, type ChatResult, type VerifiedReport } from "@/lib/types";

const DEFAULT = "What was everyone's company survey score at Samsara over the last three years?";
const EXAMPLES = [DEFAULT, "What was Engineering’s survey score?", "Did engagement increase between 2024 and 2026?", "Which department had the highest score in 2026?", "What questions were employees asked?", "How is the engagement score calculated?"];
const colors = ["#087f8c", "#5c76e8", "#d9a351"];
const format = (v: number | null | undefined) => v == null ? "—" : v.toFixed(2);
const count = (v: number | null | undefined) => v == null ? "—" : v.toLocaleString("en-US");
const signed = (v: number | null | undefined) => v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;

function Icon({ type, size = 20 }: { type: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    chart: <><path d="M4 3v17h17M8 15l4-5 4 2 5-7"/></>,
    book: <><path d="M12 5v16M3 4c4-1 6 0 9 1 3-1 5-2 9-1v15c-4-1-6 0-9 1-3-1-5-2-9-1z"/></>,
    shield: <><path d="M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/></>,
    spark: <><path d="M12 3l2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6z"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M4 16v5h16v-5"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[type] || paths.chart}</svg>;
}

export default function AnalyticsApp() {
  const [data, setData] = useState<VerifiedReport | null>(null);
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [question, setQuestion] = useState(DEFAULT);
  const [lastQuestion, setLastQuestion] = useState(DEFAULT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/report", { signal: controller.signal }).then(r => r.json()).then(result => {
      if (result.error) setError(result.error);
      else setData(result);
    }).catch(e => { if (e.name !== "AbortError") setError("The verified report could not be loaded."); });
    return () => controller.abort();
  }, []);

  async function ask(text: string, filters?: { years: number[]; departments: string[] }) {
    const id = ++sequence.current;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text, ...(filters ? { filters } : {}) }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "The workflow did not produce a verified answer.");
      if (id === sequence.current) { setData(result); setChat(result); setLastQuestion(text); setQuestion(text); }
    } catch (e) { if (id === sequence.current) setError(e instanceof Error ? e.message : "Request failed."); }
    finally { if (id === sequence.current) setBusy(false); }
  }
  function download() {
    if (!data?.report) return;
    const rows = [["Scope", "Year", "Department", "Engagement Score", "Valid Respondents", "Eligible Employees", "Response Rate", "YoY Points", "Validation", "Source Checksum"],
      ...data.report.annual.map(r => ["Aggregate", r.year, data.plan.departments.join(" + "), format(r.score), r.validRespondents, r.eligibleEmployees, format(r.responseRate), format(r.yoyChange), data.validation.status, data.validation.sourceChecksum]),
      ...data.report.departments.map(r => ["Department", r.year, r.department, format(r.score), r.validRespondents, r.eligibleEmployees, format(r.responseRate), "", data.validation.status, data.validation.sourceChecksum])];
    const csv = rows.map(r => r.map(v => `"${String(v).replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob(["SYNTHETIC DATA - not actual Samsara results\n" + csv], { type: "text/csv" }));
    const a = document.createElement("a"); a.href = url; a.download = "samsara-synthetic-survey-report.csv"; a.click(); URL.revokeObjectURL(url);
  }
  const report = data?.report;
  const latest = report?.annual.at(-1);
  const yearValue = data?.plan.years.join(",") || YEARS.join(",");
  const departmentValue = data?.plan.departments.join(",") || DEPARTMENTS.join(",");
  const companyScope = data?.plan.departments.length === DEPARTMENTS.length;
  const latestDepartments = report?.departments.filter(r => r.year === latest?.year) || [];
  const trendData = report?.annual.map(r => ({ ...r, period: `${r.year}${r.year === 2026 ? " YTD" : ""}` })) || [];
  const departmentData = (data?.plan.departments || []).map(department => ({ department, ...Object.fromEntries((data?.plan.years || []).map(year => [String(year), report?.departments.find(r => r.year === year && r.department === department)?.score])) }));

  return <div className="app-shell">
    <aside className="sidebar">
      <a href="#overview" className="brand"><span className="brand-mark">s</span><span>samsara<span className="brand-sub">PEOPLE INTELLIGENCE</span></span></a>
      <div className="workspace"><span className="workspace-icon">S</span><div>People & Culture<small>Demo workspace</small></div><span className="workspace-chevron">⌄</span></div>
      <p className="nav-label">WORKSPACE</p>
      <nav><a className="active" href="#overview"><Icon type="grid"/>Overview<span className="nav-dot"/></a><a href="#assistant"><Icon type="spark"/>Survey assistant</a><a href="#methodology"><Icon type="book"/>Methodology</a><a href="#verification"><Icon type="shield"/>Data validation</a></nav>
      <div className="sidebar-bottom"><div className="sandbox-icon"><Icon type="chart"/></div><strong>A clearer view of your people.</strong><p>Explore the story behind the scores, with evidence at every step.</p><div className="sandbox-tag"><span/>SYNTHETIC SANDBOX</div></div>
      <div className="profile"><span>PA</span><div>People Analytics<small>Local demonstration</small></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><span>Workspace <span className="breadcrumb">/</span> <strong>Survey insights</strong></span><div className="topbar-right"><span className="synthetic-badge">SYNTHETIC DATA</span><span className="avatar">PA</span></div></header>
      <main id="overview">
        <div className="page-heading"><div><div className="eyebrow">LISTEN. UNDERSTAND. IMPROVE.</div><h1>Company Engagement Score <span>— Last Three Years</span></h1><p>A shared view of engagement, grounded in every valid response.</p></div><button className="export-button" onClick={download} disabled={!report}><Icon type="download" size={16}/>Export CSV</button></div>
        <div className="context-row"><div className="context-copy"><span className="live-dot"/>Mock Qualtrics export <span className="divider">|</span> Through Oct 21, 2026</div><div className="filters"><label>Period<select aria-label="Reporting years" disabled={busy || !data} value={yearValue} onChange={e => ask(lastQuestion, { years: e.target.value.split(",").map(Number), departments: data!.plan.departments })}><option value="2024,2025,2026">Last three years</option>{YEARS.map(y => <option key={y} value={String(y)}>{y}{y === 2026 ? " YTD" : ""}</option>)}{!["2024,2025,2026", "2024", "2025", "2026"].includes(yearValue) && <option value={yearValue}>{yearValue}</option>}</select></label><label>Department<select aria-label="Department filter" disabled={busy || !data} value={departmentValue} onChange={e => ask(lastQuestion, { years: data!.plan.years, departments: e.target.value.split(",") })}><option value={DEPARTMENTS.join(",")}>All departments</option>{DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}{data && data.plan.departments.length > 1 && data.plan.departments.length < DEPARTMENTS.length && <option value={departmentValue}>{data.plan.departments.join(" + ")}</option>}</select></label></div></div>

        <section className="assistant-panel" id="assistant"><div className="assistant-heading"><div className="spark-box"><Icon type="spark"/></div><div><h2>Samsara People Analytics — Demo</h2><p>Ask naturally about scores, departments, participation or survey methodology.</p></div><span className="assistant-mode">{busy ? "Running n8n workflow…" : chat ? `Local Qwen · n8n #${chat.orchestration.executionId}` : "Local Qwen + survey RAG"}</span></div><form onSubmit={e => { e.preventDefault(); ask(question); }}><label className="sr-only" htmlFor="question">Ask about your survey</label><input id="question" value={question} onChange={e => setQuestion(e.target.value)} maxLength={500} placeholder={DEFAULT} disabled={busy}/><button className="ask-button" disabled={busy || !question.trim()}>{busy ? <span className="spinner"/> : <>Ask assistant<Icon type="arrow" size={17}/></>}</button></form><div className="suggestions"><span>Try asking</span>{EXAMPLES.slice(1).map((q, i) => <button key={q} disabled={busy} onClick={() => ask(q)}>{["Engineering scores", "Explore the trend", "Highest score", "Survey questions", "Score formula"][i]}</button>)}</div>{error && <div className="error" role="alert">{error}{report && <small>Report unchanged: the last successfully verified dataset is still displayed below.</small>}</div>}{chat && <div className="answer" aria-live="polite"><div className="answer-label"><Icon type="shield" size={17}/><strong>Verified answer</strong><span>{chat.ai.model} · grounded in verified data</span></div><p data-testid="chat-answer">{chat.answer}</p><details><summary>View {chat.references.length} supporting knowledge references</summary><p>Local Qwen interpreted the question and selected approved evidence. Numbers were calculated by TypeScript and checked against Python. Model time: {((chat.ai.interpretation.latencyMs + chat.ai.answer.latencyMs) / 1000).toFixed(1)}s.</p>{chat.references.map(r => <div className="reference" key={r.document}><strong>{r.document}</strong><p>{r.excerpt}</p></div>)}</details></div>}</section>

        <div className="section-heading"><h2>{companyScope ? "Company-wide" : data?.plan.departments.join(" + ")} engagement</h2><span>{latest?.year}{latest?.year === 2026 ? " YTD" : ""} snapshot <span className="light-dot">•</span> {count(latest?.eligibleEmployees)} eligible employees <span className="light-dot">•</span> {data?.plan.departments.length} {data?.plan.departments.length === 1 ? "department" : "departments"}</span></div>
        {!report && <div className="loading-card" role="status">{data ? `Data Validation: ${data.validation.status}. ${data.validation.message}` : error || "Loading independently verified survey metrics…"}</div>}
        {report && <>
          <section className="kpi-grid" aria-label="Key performance indicators"><article className="kpi"><div className="kpi-label">Latest engagement score <Icon type="chart" size={18}/></div><div className="kpi-value" data-testid="latest-score">{format(latest?.score)}<span>/100</span></div><p><span className="mini-dot"/> {latest?.year === 2026 ? "2026 YTD" : latest?.year} · equal respondent weighting</p></article><article className="kpi"><div className="kpi-label">Year-over-year change <span>↗</span></div><div className={`kpi-value ${(latest?.yoyChange || 0) >= 0 ? "positive" : "negative"}`}>{signed(latest?.yoyChange)}<span>pts</span></div><p>Compared with {latest ? latest.year - 1 : "prior year"} · same department scope</p></article><article className="kpi"><div className="kpi-label">Valid survey responses <span>◎</span></div><div className="kpi-value">{count(latest?.validRespondents)}<span>responses</span></div><p>Of {count(latest?.eligibleEmployees)} eligible participants · latest period</p></article><article className="kpi"><div className="kpi-label">Latest response rate <span>◷</span></div><div className="kpi-value">{format(latest?.responseRate)}<span>%</span></div><p>Valid responses ÷ eligible participants</p></article></section>

          <div className="chart-grid"><section className="panel trend-panel"><div className="panel-heading"><div><h3>Engagement over time</h3><p>A consistent measure, across every reporting period</p></div><span className="chart-unit">SCORE / 100</span></div><div className="chart"><ResponsiveContainer width="100%" height="100%" minWidth={0}><LineChart data={trendData} margin={{ left: -25, right: 25, top: 18, bottom: 5 }}><CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#e9eef1"/><XAxis dataKey="period" tickLine={false} axisLine={false} tick={{ fill: "#76818d", fontSize: 11 }} dy={12}/><YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tickLine={false} axisLine={false} tick={{ fill: "#8a95a0", fontSize: 11 }}/><Tooltip formatter={v => [`${format(Number(v))}/100`, "Engagement"]} contentStyle={{ borderRadius: 10, border: "1px solid #e2e8ed", fontSize: 12 }}/><Line dataKey="score" type="linear" name="Engagement" stroke="#087f8c" strokeWidth={3} dot={{ r: 5, fill: "#fff", strokeWidth: 3 }} activeDot={{ r: 7 }} isAnimationActive={false}/></LineChart></ResponsiveContainer></div><div className="chart-footer"><span><i className="legend-dot"/>Demo Company Engagement Score</span><strong>{signed(report.trend.change)} pts <small>across selected periods</small></strong></div></section>
          <section className="panel department-panel"><div className="panel-heading"><div><h3>Department comparison</h3><p>{data?.plan.departments.length} selected {data?.plan.departments.length === 1 ? "department" : "departments"} · one shared methodology.</p></div></div><div className="chart"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={departmentData} layout="vertical" barGap={2} margin={{ left: 0, right: 18, top: 10 }}><CartesianGrid strokeDasharray="3 4" horizontal={false} stroke="#e9eef1"/><XAxis type="number" domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fill: "#8a95a0", fontSize: 11 }}/><YAxis dataKey="department" type="category" width={155} tickLine={false} axisLine={false} tick={{ fill: "#76818d", fontSize: 11 }} interval={0}/><Tooltip formatter={v => format(Number(v))} contentStyle={{ borderRadius: 10, fontSize: 12 }}/><Legend wrapperStyle={{ fontSize: 11, paddingTop: 14 }} iconType="circle" iconSize={7}/>{data!.plan.years.map(y => <Bar key={y} name={`${y}${y === 2026 ? " YTD" : ""}`} dataKey={String(y)} fill={colors[YEARS.indexOf(y)]} radius={[0, 4, 4, 0]} maxBarSize={14} isAnimationActive={false}/>)}</BarChart></ResponsiveContainer></div></section></div>

          <div className="lower-grid"><section className="panel participation-panel"><div className="panel-heading"><div><h3>Survey participation</h3><p>Valid responses as a share of eligible participants</p></div></div><div className="participation-chart"><ResponsiveContainer width="100%" height="100%" minWidth={0}><BarChart data={trendData} layout="vertical" margin={{ left: 5, right: 25 }}><CartesianGrid strokeDasharray="3 4" horizontal={false} stroke="#e9eef1"/><XAxis type="number" domain={[0, 100]} unit="%" tickLine={false} axisLine={false} tick={{ fill: "#8a95a0", fontSize: 10 }}/><YAxis dataKey="period" type="category" tickLine={false} axisLine={false} tick={{ fill: "#76818d", fontSize: 11 }}/><Tooltip formatter={v => [`${format(Number(v))}%`, "Response rate"]}/><Bar dataKey="responseRate" fill="#39a5a6" radius={[0, 4, 4, 0]} maxBarSize={21} isAnimationActive={false}/></BarChart></ResponsiveContainer></div></section><section className="panel table-panel"><div className="panel-heading"><div><h3>Validated annual metrics</h3><p>Every displayed value is reconciled with the source.</p></div><span className="pass-tag">✓ PASS</span></div><div className="table-scroll"><table data-testid="annual-table"><thead><tr><th>Year</th><th>Engagement</th><th>Valid<br/>respondents</th><th>Eligible<br/>employees</th><th>Response<br/>rate</th><th>YoY<br/>change</th><th>Status</th></tr></thead><tbody>{report.annual.map(r => <tr key={r.year} data-testid={`annual-${r.year}`}><td>{r.year}{r.year === 2026 && <small>YTD</small>}</td><td className="score-cell">{format(r.score)}</td><td>{count(r.validRespondents)}</td><td>{count(r.eligibleEmployees)}</td><td>{format(r.responseRate)}%</td><td className={(r.yoyChange || 0) >= 0 ? "positive" : "negative"}>{r.yoyChange === null ? "—" : `${signed(r.yoyChange)} pts`}</td><td><span className="table-pass">✓ PASS</span></td></tr>)}</tbody></table></div><div className="table-foot">Pooled selected-period score <strong>{format(report.overall.score)}/100</strong><span>{count(report.overall.validRespondents)} valid responses · respondent-weighted</span></div></section></div>
          <section className="panel department-table-panel"><div className="panel-heading"><div><h3>Eligible employees by department</h3><p>{latest?.year}{latest?.year === 2026 ? " YTD" : ""} · {count(latest?.eligibleEmployees)} eligible employees in the selected scope · illustrative staffing only</p></div><span className="pass-tag">✓ PASS</span></div><div className="table-scroll"><table data-testid="department-table"><thead><tr><th>Department</th><th>Eligible employees</th><th>Valid responses</th><th>Engagement /100</th><th>Response rate</th></tr></thead><tbody>{latestDepartments.map(r => <tr key={r.department}><td>{r.department}</td><td>{count(r.eligibleEmployees)}</td><td>{count(r.validRespondents)}</td><td className="score-cell">{format(r.score)}</td><td>{format(r.responseRate)}%</td></tr>)}</tbody></table></div><div className="table-foot">Total eligible employees <strong data-testid="eligible-total">{count(latest?.eligibleEmployees)}</strong><span>Company scores weight valid respondents equally across departments.</span></div></section>
        </>}

        <section className="verification-panel" id="verification"><div className="verification-icon"><Icon type="shield" size={25}/></div><div className="verification-main"><h3>Data Validation: <span className={data?.validation.status === "PASS" ? "positive" : "negative"}>{data?.validation.status || "NOT VERIFIED"}</span></h3><p>{data?.validation.message || "Waiting for independent reconciliation."}</p>{data && <details><summary>View reconciliation receipt · {data.validation.comparisons.length} checks</summary><div className="receipt"><p>Source: {data.source}</p><p>Retrieved: {data.validation.recordsRetrieved} · Used in selected scope: {data.validation.validRecordsUsed}</p><p>Duplicate records removed: {report?.quality.duplicatesRemoved} · Invalid unique responses excluded: {report?.quality.invalidExcluded}</p><p>Checked at: {data.validation.timestamp}</p><p className="checksum">SHA-256: {data.validation.sourceChecksum}</p><div className="comparison-list">{data.validation.comparisons.map(c => <p key={c.field}><span>{c.pass ? "✓" : "✕"}</span> {c.field}: {String(c.actual)} / reference {String(c.expected)}</p>)}</div></div></details>}</div><span className="verification-side">TypeScript × Python<br/><strong>Independent calculators</strong></span></section>
        <details className="methodology" id="methodology"><summary>Understand the methodology <span>Metric definitions, reporting periods & privacy</span></summary><div><h3>A simple, reproducible score</h3><p>Respondent Score = ((QID1 + QID2 + QID3) / 3 − 1) × 25. Average all valid respondent scores equally. The pooled score includes all valid responses in the selected years. Department averages never determine company weighting.</p><p>Completed responses require three integer answers from 1 to 5. The latest submission for each ResponseID wins before validation; ties retain the later source record. Response rates use eligible headcount as the denominator.</p><p>2024 and 2025 are full calendar years. 2026 is year-to-date through October 21, 2026. Year-over-year changes use the previous calendar year under the same department filter. These periods do not establish statistical significance or causation.</p><h3>Four logical roles, one local workflow</h3><p>Local Qwen interpretation → mock Qualtrics → TypeScript analytics and Python-reference verification → Markdown retrieval → Qwen evidence selection. The RAG documents explain definitions; the deterministic engine supplies the numbers. Dashboard initialization uses the verified report API; questions and filter changes execute n8n.</p></div></details>
        <footer><span className="footer-brand">samsara <span>People Analytics — Demo</span></span><p>Entirely fabricated data. These are not Samsara’s actual employee engagement results.</p><span>Built for understanding.</span></footer>
      </main>
    </div>
  </div>;
}
