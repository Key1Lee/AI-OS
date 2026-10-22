import { DEPARTMENTS, type Reference, type VerifiedReport } from "./types";

// Formatting only. All reported values, including the trend, arrive verified.
export function buildAnswer(result: VerifiedReport, references: Reference[]): string {
  if (result.validation.status !== "PASS" || !result.report) return `Data Validation: ${result.validation.status}. ${result.validation.message}`;
  const { report, plan } = result;
  const f = (value: number | null) => value === null ? "N/A" : value.toFixed(2);
  const scope = plan.departments.length === DEPARTMENTS.length ? "Company-wide" : plan.departments.join(" and ");
  const heading = `Samsara Company Survey Results — Mock Data\n${scope} · Demo Company Engagement Score`;
  if (plan.metric === "definition") {
    const definition = references.find(r => r.document === "engagement_score_definition.md");
    return `${heading}\n\n${definition?.excerpt || "Score definition unavailable."}\n\nData Validation: PASS. Numerical results in the dashboard were independently reconciled.`;
  }
  const annual = report.annual.map(row => `${row.year}${row.year === 2026 ? " YTD" : ""}: ${plan.metric === "responseRate" ? `${f(row.responseRate)}% response rate` : `${f(row.score)}/100`} · ${row.validRespondents}/${row.eligibleEmployees} valid responses (${f(row.responseRate)}%)`).join("\n");
  const departments = plan.departments.length < DEPARTMENTS.length ? "\n\nDepartment comparison:\n" + report.departments.map(r => `${r.department}, ${r.year}: ${f(r.score)}/100 · ${r.validRespondents} valid responses`).join("\n") : "";
  const changes = report.annual.filter(r => r.yoyChange !== null).map(r => `${r.year}: ${r.yoyChange! >= 0 ? "+" : ""}${f(r.yoyChange)} points vs ${r.year - 1}`).join("; ");
  const method = plan.metric === "responseRate"
    ? references.find(r => r.document === "data_quality_rules.md")?.excerpt.split("\n").find(line => line.startsWith("Response rate ="))
    : references.find(r => r.document === "engagement_score_definition.md")?.excerpt.split("\n").filter(line => line.startsWith("Respondent Score =") || line.startsWith("Company Engagement Score =")).join(" ");
  const periodNote = plan.years.includes(2026) ? "\n2026 is YTD through October 21; no causal or significance claim is implied." : "";
  return `${heading}\n\n${annual}${departments}\n\nSelected-period trend (${report.trend.fromYear}–${report.trend.toYear}): ${report.trend.change !== null && report.trend.change >= 0 ? "+" : ""}${f(report.trend.change)} points.\nCalendar-year changes: ${changes || "No preceding calendar year in the source."}\nPooled selected-period engagement: ${f(report.overall.score)}/100 (${report.overall.validRespondents} valid responses).\n\nHow calculated: ${method || "See the supporting methodology references."}${periodNote}\n\nData Validation: PASS · independent Python reference agrees with TypeScript.`;
}
