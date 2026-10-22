import { readFile } from "node:fs/promises";
import path from "node:path";
import { datasetChecksum, projectRoot, readSnapshot } from "./data";
import { calculate } from "./metrics";
import type { Comparison, Plan, Report, Snapshot, Validation, VerifiedReport } from "./types";

export type Golden = { schemaVersion: number; sourceChecksum: string; reports: Record<string, Report> };
export function reportKey(plan: Plan): string { return [...plan.years].sort().join(",") + "|" + [...plan.departments].sort().join(","); }

export function compare(actual: unknown, expected: unknown, field = "report"): Comparison[] {
  if (typeof actual === "number" && typeof expected === "number") {
    const count = /validRespondents|eligibleEmployees|Records|Removed|Excluded|[Yy]ear/.test(field);
    return [{ field, actual, expected, pass: Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= (count ? 0 : .01) }];
  }
  if (actual !== null && expected !== null && typeof actual === "object" && typeof expected === "object") {
    if (Array.isArray(actual) !== Array.isArray(expected)) return [{ field, actual, expected, pass: false }];
    const a = actual as Record<string, unknown>, e = expected as Record<string, unknown>;
    const keys = [...new Set([...Object.keys(a), ...Object.keys(e)])];
    if (!keys.length) return [{ field, actual, expected, pass: Array.isArray(actual) === Array.isArray(expected) }];
    return keys.flatMap(k => compare(a[k], e[k], `${field}.${k}`));
  }
  return [{ field, actual: actual ?? null, expected: expected ?? null, pass: actual === expected }];
}

export function verify(report: Report, snapshot: Snapshot, plan: Plan, golden: Golden | null, approvedChecksum: string): Validation {
  const sourceChecksum = datasetChecksum(snapshot);
  const base = { sourceChecksum, recordsRetrieved: snapshot.responses.length, validRecordsUsed: report.overall.validRespondents, timestamp: new Date().toISOString() };
  if (!golden) return { ...base, status: "NOT VERIFIED", comparisons: [], message: "Independent Python reference is unavailable. Numerical findings are withheld." };
  const comparisons: Comparison[] = [
    { field: "schemaVersion", actual: golden.schemaVersion, expected: 1, pass: golden.schemaVersion === 1 },
    { field: "sourceChecksum", actual: sourceChecksum, expected: golden.sourceChecksum, pass: sourceChecksum === golden.sourceChecksum },
    { field: "approvedFixtureChecksum", actual: sourceChecksum, expected: approvedChecksum, pass: sourceChecksum === approvedChecksum },
    ...compare(report, golden.reports[reportKey(plan)]),
  ];
  const pass = comparisons.every(c => c.pass);
  return { ...base, status: pass ? "PASS" : "FAIL", comparisons, message: pass ? "TypeScript metrics match the independent Python reference for the same dataset." : "Reconciliation failed. Numerical findings are withheld." };
}

export async function verifiedReport(plan: Plan, incoming?: Snapshot): Promise<VerifiedReport> {
  const approved = await readSnapshot(), snapshot = incoming || approved;
  if (!Array.isArray(snapshot.responses) || !Array.isArray(snapshot.headcount)) throw new Error("Invalid Mock Qualtrics export.");
  if (!snapshot.responses.length) throw new Error("No survey records were retrieved.");
  const report = calculate(snapshot, plan);
  if (report.annual.some(r => !r.validRespondents || !r.eligibleEmployees)) throw new Error("No valid survey records or eligible headcount for a requested reporting period.");
  let golden: Golden | null = null;
  try { golden = JSON.parse(await readFile(path.join(projectRoot, "fixtures/golden_report.json"), "utf8")); } catch { /* Never convert unavailable validation to PASS. */ }
  let validation: Validation;
  try { validation = verify(report, snapshot, plan, golden, datasetChecksum(approved)); }
  catch { validation = { status: "NOT VERIFIED", sourceChecksum: datasetChecksum(snapshot), recordsRetrieved: snapshot.responses.length,
    validRecordsUsed: report.overall.validRespondents, comparisons: [], timestamp: new Date().toISOString(), message: "Malformed independent reference. Numerical findings are withheld." }; }
  return { report: validation.status === "PASS" ? report : null, validation, plan, source: "Mock Qualtrics Survey Export · synthetic data only" };
}
