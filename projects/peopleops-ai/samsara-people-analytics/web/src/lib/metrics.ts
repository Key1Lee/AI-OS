import { DEPARTMENTS, YEARS, type Aggregate, type Plan, type Report, type Snapshot, type SurveyResponse } from "./types";

export function deduplicate(responses: SurveyResponse[]): SurveyResponse[] {
  const latest = new Map<string, SurveyResponse>();
  for (const row of responses) {
    const previous = latest.get(row.ResponseID);
    if (!previous || Date.parse(row.RecordedDate) >= Date.parse(previous.RecordedDate)) latest.set(row.ResponseID, row);
  }
  return [...latest.values()];
}

export function isValid(row: SurveyResponse): boolean {
  const stamp = new Date(row.RecordedDate);
  return row.Finished === 1 && YEARS.includes(row.SurveyYear) && DEPARTMENTS.includes(row.Department)
    && Number.isFinite(stamp.getTime()) && stamp.getUTCFullYear() === row.SurveyYear
    && (row.SurveyYear !== 2026 || stamp <= new Date("2026-10-21T23:59:59.999Z"))
    && [row.QID1, row.QID2, row.QID3].every(s => typeof s === "number" && Number.isInteger(s) && s >= 1 && s <= 5);
}

export function respondentScore(row: SurveyResponse): number {
  return (((row.QID1! + row.QID2! + row.QID3!) / 3) - 1) * 25;
}

export function calculate(snapshot: Snapshot, plan: Plan): Report {
  const unique = deduplicate(snapshot.responses);
  const valid = unique.filter(isValid);
  function aggregate(year: number, departments: string[]): Aggregate {
    const respondents = valid.filter(r => r.SurveyYear === year && departments.includes(r.Department));
    const eligibleEmployees = snapshot.headcount.filter(h => h.SurveyYear === year && departments.includes(h.Department)).reduce((n, h) => n + h.EligibleEmployees, 0);
    return { year, score: respondents.length ? respondents.reduce((n, r) => n + respondentScore(r), 0) / respondents.length : null,
      validRespondents: respondents.length, eligibleEmployees, responseRate: eligibleEmployees ? respondents.length / eligibleEmployees * 100 : null };
  }
  const annual = plan.years.map(year => {
    const row = aggregate(year, plan.departments), previous = aggregate(year - 1, plan.departments);
    return { ...row, yoyChange: row.score !== null && previous.score !== null ? row.score - previous.score : null };
  });
  const selected = valid.filter(r => plan.years.includes(r.SurveyYear) && plan.departments.includes(r.Department));
  const eligibleEmployees = annual.reduce((n, r) => n + r.eligibleEmployees, 0);
  return { annual, trend: { fromYear: plan.years[0], toYear: plan.years[plan.years.length - 1], change: annual.at(-1)!.score !== null && annual[0].score !== null ? annual.at(-1)!.score! - annual[0].score : null }, departments: plan.years.flatMap(year => plan.departments.map(department => ({ ...aggregate(year, [department]), department }))),
    overall: { score: selected.length ? selected.reduce((n, r) => n + respondentScore(r), 0) / selected.length : null, validRespondents: selected.length, eligibleEmployees,
      responseRate: eligibleEmployees ? selected.length / eligibleEmployees * 100 : null },
    quality: { retrievedRecords: snapshot.responses.length, deduplicatedRecords: unique.length, duplicatesRemoved: snapshot.responses.length - unique.length,
      invalidExcluded: unique.length - valid.length, validRecordsUsed: selected.length } };
}
