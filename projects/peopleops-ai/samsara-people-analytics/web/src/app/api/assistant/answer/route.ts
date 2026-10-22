import { body, failure, json } from "@/lib/http";
import { groundedAnswer, INTENTS, validateQuestion, type Interpretation } from "@/lib/assistant";
import { QwenError } from "@/lib/qwen";
import { filterPlan } from "@/lib/request";
import { retrieve } from "@/lib/rag";
import { compare, verifiedReport } from "@/lib/verification";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  try {
    const input = await body(request);
    const question = validateQuestion({ question: input.question });
    const interpretation = input.interpretation as Interpretation;
    if (!interpretation || !INTENTS.includes(interpretation.intent) || typeof interpretation.retrievalQuery !== "string" || interpretation.retrievalQuery.length > 500)
      throw new Error("A bounded Qwen interpretation is required.");
    const plan = filterPlan({ years: interpretation.plan?.years, departments: interpretation.plan?.departments });
    plan.metric = interpretation.intent === "participation" ? "responseRate" : interpretation.intent === "knowledge" ? "definition" : "engagement";
    if (input.metrics?.validation?.status !== "PASS" || !input.metrics.report)
      return json({ error: input.metrics?.validation?.message || "Numerical validation did not pass.", report: null, validation: input.metrics?.validation || { status: "NOT VERIFIED" } }, 409);
    const result = await verifiedReport(plan);
    if (result.validation.status !== "PASS") return json({ error: result.validation.message, ...result }, 409);
    if (input.metrics.validation.sourceChecksum !== result.validation.sourceChecksum || !compare(input.metrics.report, result.report).every(c => c.pass))
      throw new QwenError("The supplied metrics do not match the approved verified report.", 409);
    // Re-read approved documents so caller-supplied text cannot inject evidence.
    const references = await retrieve(interpretation.retrievalQuery);
    if (!Array.isArray(input.references) || JSON.stringify(input.references) !== JSON.stringify(references)) throw new QwenError("Retrieved evidence differs from the approved knowledge documents.");
    return json({ ...result, ...await groundedAnswer(question, interpretation, result, references), references });
  } catch (error) { return failure(error, error instanceof QwenError ? error.status : 400); }
}
