export const YEARS = [2024, 2025, 2026];
export const DEPARTMENTS = ["Human Resources", "Marketing", "Engineering & Product", "Sales", "Customer Success & Support"];
export type Plan = { years: number[]; departments: string[]; metric: "engagement" | "responseRate" | "definition" };
export type SurveyResponse = {
  ResponseID: string; RecordedDate: string; SurveyYear: number; Department: string;
  Finished: number; QID1: number | null; QID2: number | null; QID3: number | null;
};
export type Headcount = { SurveyYear: number; Department: string; EligibleEmployees: number };
export type Snapshot = { responses: SurveyResponse[]; headcount: Headcount[] };
export type Aggregate = { year: number; score: number | null; validRespondents: number; eligibleEmployees: number; responseRate: number | null };
export type Report = {
  annual: (Aggregate & { yoyChange: number | null })[];
  trend: { fromYear: number; toYear: number; change: number | null };
  departments: (Aggregate & { department: string })[];
  overall: Omit<Aggregate, "year">;
  quality: { retrievedRecords: number; deduplicatedRecords: number; duplicatesRemoved: number; invalidExcluded: number; validRecordsUsed: number };
};
export type Comparison = { field: string; actual: unknown; expected: unknown; pass: boolean };
export type Validation = {
  status: "PASS" | "FAIL" | "NOT VERIFIED"; sourceChecksum: string;
  recordsRetrieved: number; validRecordsUsed: number; comparisons: Comparison[]; timestamp: string; message: string;
};
export type VerifiedReport = { report: Report | null; validation: Validation; plan: Plan; source: string };
export type Reference = { document: string; excerpt: string; relevance: number };
export type ChatResult = VerifiedReport & {
  answer: string; references: Reference[];
  ai: { provider: "qwen_local"; model: string; grounding: "validated evidence selection";
    interpretation: import("./qwen").ModelReceipt; answer: import("./qwen").ModelReceipt;
    selectedEvidence: { factIds: string[]; passageIds: string[] } };
  orchestration: { mode: "n8n"; executionId: string; workflowId: string };
};
