import { body, failure, json } from "@/lib/http";
import { retrieve } from "@/lib/rag";
export async function POST(request: Request) {
  try {
    const { question } = await body(request);
    if (typeof question !== "string" || question.length > 500) throw new Error("A question of up to 500 characters is required.");
    return json({ references: await retrieve(question), numericalSource: false });
  } catch (error) { return failure(error); }
}
