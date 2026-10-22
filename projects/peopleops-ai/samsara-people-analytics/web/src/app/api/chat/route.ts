import { body, failure, json } from "@/lib/http";
import { ChatError, orchestrate } from "@/lib/chat";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  try { return json(await orchestrate(await body(request))); }
  catch (error) {
    if (error instanceof ChatError && error.validation) return json({ error: error.message, report: null, validation: error.validation }, error.status);
    return failure(error, error instanceof ChatError ? error.status : 400);
  }
}
