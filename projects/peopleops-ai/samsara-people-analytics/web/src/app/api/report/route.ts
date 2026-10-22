import { failure, json } from "@/lib/http";
import { filterPlan } from "@/lib/request";
import { verifiedReport } from "@/lib/verification";
export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  try {
    const q = new URL(request.url).searchParams;
    if ([...q.keys()].some(k => !["years", "departments"].includes(k))) throw new Error("Unknown report filter.");
    const plan = filterPlan({ ...(q.has("years") ? { years: q.get("years")!.split(",").map(Number) } : {}),
      ...(q.has("departments") ? { departments: q.get("departments")!.split(",") } : {}) });
    const result = await verifiedReport(plan);
    return json(result, result.validation.status === "PASS" ? 200 : 409);
  } catch (error) { return failure(error, 422); }
}
