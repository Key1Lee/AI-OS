import { body, failure, json } from "@/lib/http";
import { interpret } from "@/lib/assistant";
import { QwenError } from "@/lib/qwen";
export const dynamic = "force-dynamic";
export async function POST(request: Request) {
  try { return json(await interpret(await body(request))); }
  catch (error) { return failure(error, error instanceof QwenError ? error.status : 400); }
}
