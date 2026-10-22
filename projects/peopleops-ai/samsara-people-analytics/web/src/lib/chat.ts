import { validateQuestion } from "./assistant";
import type { ChatResult } from "./types";

export class ChatError extends Error { constructor(message: string, public status: number, public validation?: ChatResult["validation"]) { super(message); } }
export async function orchestrate(input: { question?: unknown; filters?: unknown }, webhook = process.env.N8N_WEBHOOK_URL || "http://localhost:5678/webhook/samsara-survey", timeoutMs = 80000): Promise<ChatResult> {
  validateQuestion(input);
  let response: Response;
  try { response = await fetch(webhook, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input), signal: AbortSignal.timeout(timeoutMs), cache: "no-store" }); }
  catch { throw new ChatError("n8n is unavailable or timed out. Start Docker Compose and retry. No n8n execution or verified chat answer was completed.", 503); }
  let data;
  try { data = await response.json(); } catch { throw new ChatError("n8n returned an invalid response. Check workflow activation and execution logs.", 502); }
  if (!response.ok || data.error) throw new ChatError(`${data.validation?.status === "FAIL" ? "Data Validation: FAIL. " : ""}${data.error || "n8n workflow failed. No verified answer was produced."}`, response.status >= 400 ? response.status : 502, data.validation?.status === "FAIL" ? data.validation : undefined);
  if (data.validation?.status !== "PASS" || !data.report || !data.orchestration?.executionId || data.orchestration?.mode !== "n8n" || data.ai?.provider !== "qwen_local" || !data.ai?.model || !data.ai?.interpretation || !data.ai?.answer)
    throw new ChatError(`Data Validation: ${data.validation?.status || "NOT VERIFIED"}. ${data.validation?.message || "A verified n8n execution was not returned."}`, 409);
  return data as ChatResult;
}
