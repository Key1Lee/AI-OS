export class QwenError extends Error {
  constructor(message: string, public status = 502) { super(message); }
}
export type ModelReceipt = { provider: "qwen_local"; model: string; latencyMs: number; inputTokens: number; outputTokens: number };
type Schema = Record<string, unknown>;

// Reuse the existing Mac llama.cpp runtime. A question cannot select a provider,
// URL, model, tool or credential. There is no cloud or deterministic chat fallback.
export async function askQwen(system: string, evidence: unknown, schema: Schema, transport: typeof fetch = fetch): Promise<{ value: unknown; receipt: ModelReceipt }> {
  const base = new URL(process.env.QWEN_BASE_URL || "http://127.0.0.1:8080/v1");
  if (base.protocol !== "http:" || !["127.0.0.1", "localhost", "host.docker.internal"].includes(base.hostname) || base.username || base.password || base.search || base.hash || base.pathname.replace(/\/$/, "") !== "/v1")
    throw new QwenError("Qwen must use the configured local /v1 runtime endpoint.");
  const model = process.env.QWEN_MODEL || "Qwen3-4B-Q4_K_M";
  const started = Date.now();
  let response: Response;
  try {
    response = await transport(base.href.replace(/\/$/, "") + "/chat/completions", {
      method: "POST", headers: { "Content-Type": "application/json" }, redirect: "error", cache: "no-store",
      signal: AbortSignal.timeout(30000),
      body: JSON.stringify({ model, messages: [{ role: "system", content: system }, { role: "user", content: JSON.stringify(evidence) }],
        temperature: 0, max_completion_tokens: 650, stream: false, store: false,
        chat_template_kwargs: { enable_thinking: false },
        response_format: { type: "json_schema", json_schema: { name: "survey_evidence", strict: true, schema } } }),
    });
  } catch { throw new QwenError("Local Qwen is unavailable or timed out. Start the existing AI-OS Qwen runtime on the Mac and retry. No AI answer was produced.", 503); }
  if (!response.ok) throw new QwenError(`Local Qwen returned HTTP ${response.status}. No AI answer was produced.`, 503);
  const text = await response.text();
  if (text.length > 64000) throw new QwenError("Local Qwen returned an oversized response.");
  try {
    const data = JSON.parse(text), choice = data.choices?.[0];
    if (data.model !== model || choice?.finish_reason !== "stop" || choice.message?.tool_calls || typeof choice.message?.content !== "string" ||
        !Number.isInteger(data.usage?.prompt_tokens) || !Number.isInteger(data.usage?.completion_tokens)) throw new Error();
    return { value: JSON.parse(choice.message.content), receipt: { provider: "qwen_local", model, latencyMs: Date.now() - started,
      inputTokens: data.usage.prompt_tokens, outputTokens: data.usage.completion_tokens } };
  } catch { throw new QwenError("Local Qwen returned incomplete or invalid structured output. No grounded answer was produced."); }
}
