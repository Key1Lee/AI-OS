import test from "node:test";
import assert from "node:assert/strict";
import { evidenceFacts, passageFacts, validateInterpretation, validateQuestion, validateSelection } from "../web/src/lib/assistant";
import { askQwen, QwenError } from "../web/src/lib/qwen";
import { verifiedReport } from "../web/src/lib/verification";
import { retrieve } from "../web/src/lib/rag";
import { DEPARTMENTS, YEARS } from "../web/src/lib/types";

const proposal = { supported: true, years: YEARS, departments: ["Engineering & Product"], intent: "score", retrievalQuery: "Engineering survey engagement score formula" };
test("free-form input accepts possessives, shorthand and general survey questions without a word list", () => {
  for (const question of ["What was Engineering’s Survey Score", "How'd eng do lately?", "Which team scored highest?", "Why exclude unfinished submissions?", "What were employees asked?", "How many eligible employees were there?"])
    assert.equal(validateQuestion({ question }), question);
  for (const question of ["individual employee score", "employee's name", "survey in 2023", "survey http://localhost", "SELECT score FROM responses"])
    assert.throws(() => validateQuestion({ question }));
  assert.throws(() => validateQuestion({ question: "survey", filters: { departments: ["Finance"] } }));
});
test("model query proposals are allowlisted and explicit filter controls take precedence", () => {
  assert.deepEqual(validateInterpretation(proposal).plan.departments, ["Engineering & Product"]);
  const filtered = validateInterpretation(proposal, { years: [2025], departments: ["Sales"] });
  assert.deepEqual(filtered.plan, { years: [2025], departments: ["Sales"], metric: "engagement" });
  for (const change of [{ departments: ["Finance"] }, { years: [2027] }, { intent: "executeSQL" }, { url: "http://evil" }, { retrievalQuery: "" }])
    assert.throws(() => validateInterpretation({ ...proposal, ...change }));
  assert.throws(() => validateInterpretation({ ...proposal, supported: false }), (e: unknown) => e instanceof QwenError && e.status === 400);
});
test("Qwen can select only exact verified facts and retrieved passages; invented numbers cannot enter the answer", async () => {
  const result = await verifiedReport({ years: YEARS, departments: DEPARTMENTS, metric: "engagement" });
  const facts = evidenceFacts(result), passages = passageFacts(await retrieve("survey score formula"));
  assert(facts.some(f => f.id === "ranking-2026"));
  for (const row of result.report!.annual) assert(facts.find(f => f.id === `score-${row.year}`)!.text.includes(row.score!.toFixed(2)));
  const selection = { factIds: ["score-2026"], passageIds: [passages[0].id] };
  assert.deepEqual(validateSelection(selection, facts, passages, "score"), selection);
  for (const invalid of [{ ...selection, factIds: ["99.99"] }, { ...selection, prose: "Score is 99.99" }, { ...selection, passageIds: ["private-document"] }, { ...selection, factIds: ["score-2026", "score-2026"] }])
    assert.throws(() => validateSelection(invalid, facts, passages, "score"));
  assert.throws(() => validateSelection({ factIds: [], passageIds: [] }, facts, passages, "knowledge"));
  assert.throws(() => evidenceFacts({ ...result, report: null, validation: { ...result.validation, status: "FAIL" } }));
});
test("local Qwen transport validates actual model, completed structured output and usage; outages fail explicitly", async () => {
  const payload = { model: "Qwen3-4B-Q4_K_M", choices: [{ finish_reason: "stop", message: { content: '{"supported":true}' } }], usage: { prompt_tokens: 25, completion_tokens: 5 } };
  const transport: typeof fetch = async (url, options) => {
    assert.match(String(url), /^http:\/\/(127\.0\.0\.1|localhost|host\.docker\.internal):\d+\/v1\/chat\/completions$/);
    assert.equal(options?.redirect, "error");
    const request = JSON.parse(options!.body as string);
    assert.equal(request.chat_template_kwargs.enable_thinking, false);
    assert.equal(request.response_format.type, "json_schema");
    return Response.json(payload);
  };
  assert.equal((await askQwen("select", {}, {}, transport)).receipt.provider, "qwen_local");
  for (const change of [{ model: "different-model" }, { choices: [{ finish_reason: "length", message: { content: "{}" } }] }, { usage: null }])
    await assert.rejects(askQwen("select", {}, {}, async () => Response.json({ ...payload, ...change })), /invalid structured/);
  await assert.rejects(askQwen("select", {}, {}, async () => { throw new Error("offline"); }), (e: unknown) => e instanceof QwenError && e.status === 503 && /No AI answer/.test(e.message));
});
