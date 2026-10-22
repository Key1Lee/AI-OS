import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import type { Snapshot } from "./types";

export const projectRoot = process.env.DEMO_ROOT || path.resolve(process.cwd(), "..");
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`).join(",")}}`;
  return JSON.stringify(value);
}
export function datasetChecksum(snapshot: Snapshot): string {
  return createHash("sha256").update(canonical(snapshot)).digest("hex");
}
export async function readSnapshot(): Promise<Snapshot> {
  const [responses, headcount] = await Promise.all(["qualtrics_responses.json", "eligible_headcount.json"].map(file => readFile(path.join(projectRoot, "fixtures", file), "utf8").then(JSON.parse)));
  return { responses, headcount };
}
