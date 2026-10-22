import { datasetChecksum, readSnapshot } from "@/lib/data";
import { failure, json } from "@/lib/http";
export const dynamic = "force-dynamic";
export async function GET() {
  try { const snapshot = await readSnapshot(); return json({ ...snapshot, sourceChecksum: datasetChecksum(snapshot), synthetic: true }); }
  catch { return failure(new Error("Mock Qualtrics fixture is unavailable."), 503); }
}
