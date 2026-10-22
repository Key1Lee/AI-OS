export const json = (value: unknown, status = 200) => Response.json(value, { status, headers: { "Cache-Control": "no-store" } });
export const failure = (error: unknown, status = 400) => json({ error: error instanceof Error ? error.message : "Request failed", validation: { status: "NOT VERIFIED" } }, status);
export async function body(request: Request) {
  const text = await request.text();
  if (Buffer.byteLength(text, "utf8") > 8_000_000) throw new Error("Request body exceeds the 8 MB demo limit.");
  const value = JSON.parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("JSON object required.");
  return value;
}
