import { body, failure, json } from "@/lib/http";
import { filterPlan } from "@/lib/request";
import { verifiedReport } from "@/lib/verification";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  try {
    const input = await body(request);
    if (!input.plan || typeof input.plan !== "object" || Array.isArray(input.plan) || Object.keys(input.plan).some(k => !["years", "departments", "metric"].includes(k))) throw new Error("A restricted metric query plan is required.");
    if (input.plan.metric !== undefined && !["engagement", "definition", "responseRate"].includes(input.plan.metric)) throw new Error("Unsupported metric.");
    const plan = filterPlan({ years: input.plan?.years, departments: input.plan?.departments });
    if (["engagement", "definition", "responseRate"].includes(input.plan?.metric)) plan.metric = input.plan.metric;
    if (!input.snapshot || !Array.isArray(input.snapshot.responses) || !Array.isArray(input.snapshot.headcount)) throw new Error("A complete mock export snapshot is required.");
    const result = await verifiedReport(plan, { responses: input.snapshot.responses, headcount: input.snapshot.headcount });
    return json(result, result.validation.status === "PASS" ? 200 : 409);
  } catch (error) { return failure(error, 422); }
}
