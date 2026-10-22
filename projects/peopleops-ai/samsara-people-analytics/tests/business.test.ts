import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";
import { calculate, deduplicate, isValid, respondentScore } from "../web/src/lib/metrics";
import { datasetChecksum, projectRoot, readSnapshot } from "../web/src/lib/data";
import { compare, reportKey, verify, verifiedReport, type Golden } from "../web/src/lib/verification";
import { parseRequest } from "../web/src/lib/request";
import { retrieve } from "../web/src/lib/rag";
import { buildAnswer } from "../web/src/lib/answer";
import { ChatError, orchestrate } from "../web/src/lib/chat";
import { body } from "../web/src/lib/http";
import { DEPARTMENTS, YEARS, type Plan, type Snapshot, type SurveyResponse } from "../web/src/lib/types";

const snapshot = await readSnapshot();
const golden: Golden = JSON.parse(await readFile(path.join(projectRoot, "fixtures/golden_report.json"), "utf8"));
const full: Plan = { years: YEARS, departments: DEPARTMENTS, metric: "engagement" };
const row = (overrides = {}): SurveyResponse => ({ ResponseID: "R_TEST", RecordedDate: "2025-04-01T12:00:00Z", SurveyYear: 2025, Department: "Engineering & Product", Finished: 1, QID1: 3, QID2: 3, QID3: 3, ...overrides });

test("all 217 Python reference scopes reconcile every report field and source checksum", () => {
  assert.equal(datasetChecksum(snapshot), golden.sourceChecksum);
  assert.equal(Object.keys(golden.reports).length, 217);
  const approvedChecksum = datasetChecksum(snapshot);
  for (const key of Object.keys(golden.reports)) {
    const [ys, ds] = key.split("|");
    const plan: Plan = { years: ys.split(",").map(Number), departments: DEPARTMENTS.filter(d => ds.split(",").includes(d)), metric: "engagement" };
    assert.equal(verify(calculate(snapshot, plan), snapshot, plan, golden, approvedChecksum).status, "PASS", key);
  }
});

test("5,000 eligible employees per year across five unequal department cohorts", () => {
  const allocation = new Map([["Human Resources", 250], ["Marketing", 500], ["Engineering & Product", 2000], ["Sales", 1250], ["Customer Success & Support", 1000]]);
  assert.equal(DEPARTMENTS.length, 5);
  for (const year of YEARS) {
    const cohorts = snapshot.headcount.filter(h => h.SurveyYear === year);
    assert.equal(cohorts.length, 5);
    assert.equal(cohorts.reduce((n, c) => n + c.EligibleEmployees, 0), 5000);
    for (const cohort of cohorts) assert.equal(cohort.EligibleEmployees, allocation.get(cohort.Department));
  }
  const report = calculate(snapshot, full);
  assert.equal(report.overall.eligibleEmployees, 15000);
  assert(report.annual.every(r => r.eligibleEmployees === 5000 && r.validRespondents <= 5000));
});

test("large fixture passes the bounded HTTP parser; oversized bodies are rejected", async () => {
  const payload = JSON.stringify({ snapshot, plan: full });
  assert(Buffer.byteLength(payload) > 1_000_000);
  assert(Buffer.byteLength(payload) < 8_000_000);
  const parsed = await body(new Request("http://demo.test/api/metrics", { method: "POST", body: payload }));
  assert.equal(parsed.snapshot.responses.length, snapshot.responses.length);
  await assert.rejects(body(new Request("http://demo.test/api/metrics", { method: "POST", body: " ".repeat(8_000_001) })), /8 MB/);
});

test("respondent formula maps 1 to 0, 3 to 50 and 5 to 100", () => {
  for (const [score, expected] of [[1, 0], [3, 50], [5, 100]]) assert.equal(respondentScore(row({ QID1: score, QID2: score, QID3: score })), expected);
});
test("completion, missing, fractional, invalid and YTD cutoff rules", () => {
  for (const value of [{ Finished: 0 }, { QID1: null }, { QID2: 6 }, { QID3: 2.5 }, { QID1: true }, { Department: "Finance" }, { RecordedDate: "bad" }, { SurveyYear: 2026 }, { SurveyYear: 2026, RecordedDate: "2026-10-22T00:00:00Z" }]) assert.equal(isValid(row(value)), false);
  assert.equal(isValid(row({ SurveyYear: 2026, RecordedDate: "2026-10-21T23:59:59Z" })), true);
});
test("deduplicate before validation; latest invalid revision supersedes earlier valid", () => {
  const early = row(), late = row({ RecordedDate: "2025-04-02T12:00:00Z", QID3: null });
  assert.deepEqual(deduplicate([late, early]), [late]);
  assert.equal(deduplicate([early, late]).filter(isValid).length, 0);
  assert.deepEqual(deduplicate([early, row({ QID1: 5 })])[0].QID1, 5);
});
test("company and pooled averages weight respondents, never department means", () => {
  const unequal: Snapshot = { responses: [row({ ResponseID: "A", QID1: 5, QID2: 5, QID3: 5 }), ...[1, 2, 3].map(i => row({ ResponseID: `B${i}`, Department: "Sales", QID1: 1, QID2: 1, QID3: 1 }))],
    headcount: [{ SurveyYear: 2025, Department: "Engineering & Product", EligibleEmployees: 60 }, { SurveyYear: 2025, Department: "Sales", EligibleEmployees: 60 }] };
  const result = calculate(unequal, { ...full, years: [2025], departments: ["Engineering & Product", "Sales"] });
  assert.equal(result.annual[0].score, 25);
  assert.equal(result.overall.score, 25);
  assert.equal(result.overall.eligibleEmployees, 120);
  assert.equal(result.overall.responseRate, 4 / 120 * 100);
});
test("negative test: tampered application score is FAIL", () => {
  const result = calculate(snapshot, full); result.annual[0].score! += 1;
  const validation = verify(result, snapshot, full, golden, datasetChecksum(snapshot));
  assert.equal(validation.status, "FAIL");
  assert(validation.comparisons.some(c => c.field === "report.annual.0.score" && !c.pass));
});
test("corrupted reference, incomplete reference, changed headcount and stale source are rejected", () => {
  const corrupt = structuredClone(golden); corrupt.reports[reportKey(full)].overall.score! += 5;
  assert.equal(verify(calculate(snapshot, full), snapshot, full, corrupt, datasetChecksum(snapshot)).status, "FAIL");
  assert.equal(verify(calculate(snapshot, full), snapshot, full, { ...golden, reports: {} }, datasetChecksum(snapshot)).status, "FAIL");
  const changed = structuredClone(snapshot); changed.headcount[0].EligibleEmployees++;
  assert.equal(verify(calculate(changed, full), changed, full, golden, datasetChecksum(snapshot)).status, "FAIL");
  const removed = { ...snapshot, responses: snapshot.responses.slice(1) };
  assert.equal(verify(calculate(removed, full), removed, full, golden, datasetChecksum(snapshot)).status, "FAIL");
});
test("missing reference is NOT VERIFIED; count comparisons are exact", () => {
  assert.equal(verify(calculate(snapshot, full), snapshot, full, null, datasetChecksum(snapshot)).status, "NOT VERIFIED");
  assert.equal(compare({ validRespondents: 20.001 }, { validRespondents: 20 })[0].pass, false);
  assert.equal(compare({ score: 50.009 }, { score: 50 })[0].pass, true);
});
test("missing survey records fail and mismatched source withholds report", async () => {
  await assert.rejects(verifiedReport(full, { responses: [], headcount: snapshot.headcount }), /No survey records/);
  const changed = structuredClone(snapshot); changed.responses[0].QID1 = 1;
  const result = await verifiedReport(full, changed);
  assert.equal(result.validation.status, "FAIL"); assert.equal(result.report, null);
});

const examples = ["What was everyone's company survey score at Samsara over the last three years?", "Compare Engineering & Product and Sales engagement scores in 2025.", "Did engagement increase between 2024 and 2026?", "How is the engagement score calculated?", "What was the company-wide survey response rate?"];
test("the five required questions produce bounded, deterministic plans", () => {
  assert.deepEqual(parseRequest({ question: examples[0] }), full);
  assert.deepEqual(parseRequest({ question: examples[1] }), { years: [2025], departments: ["Engineering & Product", "Sales"], metric: "engagement" });
  assert.deepEqual(parseRequest({ question: examples[2] }).years, YEARS);
  assert.equal(parseRequest({ question: examples[3] }).metric, "definition");
  assert.equal(parseRequest({ question: examples[4] }).metric, "responseRate");
});
test("all canonical department names, ampersands, and legacy shorthand resolve correctly", () => {
  for (const department of DEPARTMENTS) {
    assert.deepEqual(parseRequest({ question: `What was ${department} engagement in 2025?` }).departments, [department]);
  }
  assert.deepEqual(parseRequest({ question: "HR survey scores in 2025" }).departments, ["Human Resources"]);
  assert.deepEqual(parseRequest({ question: "Engineering engagement in 2025" }).departments, ["Engineering & Product"]);
  assert.deepEqual(parseRequest({ question: "Customer Support engagement in 2025" }).departments, ["Customer Success & Support"]);
});
test("three selected departments are a partial scope; all five are company-wide", async () => {
  const refs = await retrieve(examples[0]);
  const complete = await verifiedReport(full);
  assert(buildAnswer(complete, refs).includes("Company-wide"));
  assert(!buildAnswer(complete, refs).includes("Department comparison:"));
  const scoped = await verifiedReport({ ...full, departments: DEPARTMENTS.slice(0, 3) });
  assert(!buildAnswer(scoped, refs).includes("Company-wide"));
  assert(buildAnswer(scoped, refs).includes("Department comparison:"));
});
test("unknown departments, unsupported periods, individual answers and SQL/URLs are rejected", () => {
  for (const question of ["Finance engagement in 2025", "Compare Engineering and Finance engagement scores in 2025", "engagement in 2023", "individual employee survey scores", "SELECT survey score", "survey score http://web:3000", "what is the weather"]) assert.throws(() => parseRequest({ question }));
  assert.throws(() => parseRequest({ question: examples[0], filters: { departments: ["Finance"] } }));
  assert.throws(() => parseRequest({ question: examples[0], filters: { years: [] } }));
});
test("formula retrieval is ranked first and grounded answers only format verified numbers", async () => {
  const refs = await retrieve(examples[3]);
  assert.equal(refs[0].document, "engagement_score_definition.md");
  assert.match(refs[0].excerpt, /QID1 \+ QID2 \+ QID3/);
  const result = await verifiedReport(full);
  const answer = buildAnswer(result, refs);
  assert(answer.includes("Respondent Score = ((QID1 + QID2 + QID3) / 3 - 1) × 25."));
  for (const r of result.report!.annual) assert(answer.includes(`${r.score!.toFixed(2)}/100`));
  assert(!buildAnswer({ ...result, report: null, validation: { ...result.validation, status: "FAIL" } }, refs).includes("/100"));
});
test("generated workflow executes Qwen services and attaches only verified execution receipts", async () => {
  const workflow = JSON.parse(await readFile(path.join(projectRoot, "n8n/qualtrics-survey-demo.json"), "utf8"));
  for (const name of ["Qwen Interpret Question", "Qwen Grounded Answer"]) {
    const node = workflow.nodes.find((n: { name: string }) => n.name === name);
    assert.equal(node.type, "n8n-nodes-base.httpRequest");
    assert.match(node.parameters.url, /http:\/\/web:3000\/api\/assistant\//);
  }
  const code = workflow.nodes.find((n: { name: string }) => n.name === "Attach Execution Receipt").parameters.jsCode;
  const result = { ...await verifiedReport(full), ai: { provider: "qwen_local" } };
  const run = (data: unknown) => vm.runInNewContext(`(function(){${code}})()`, { $json: data, $execution: { id: "test" }, $workflow: { id: "workflow" } })[0].json;
  assert.equal(run(result).orchestration.executionId, "test");
  assert.equal(run({ error: "Qwen unavailable", statusCode: 503 }).statusCode, 503);
  assert.equal(run({ ...result, validation: { status: "FAIL" }, report: null }).statusCode, 409);
});
test("unavailable n8n produces an explicit 503 with no fallback claim", async () => {
  await assert.rejects(orchestrate({ question: examples[0] }, "http://127.0.0.1:1/webhook", 100), (error: unknown) => error instanceof ChatError && error.status === 503 && /No n8n execution/.test(error.message));
});
