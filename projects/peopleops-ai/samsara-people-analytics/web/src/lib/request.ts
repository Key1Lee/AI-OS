import { DEPARTMENTS, type Plan } from "./types";

// Legacy deterministic examples and strict filter validation. Free-form chat
// interpretation is performed by local Qwen in assistant.ts.
export function parseRequest(input: { question?: unknown; filters?: unknown }): Plan {
  const allowedYears = [2024, 2025, 2026];
  const allowedDepartments = DEPARTMENTS;
  if (typeof input?.question !== "string" || !input.question.trim() || input.question.length > 500)
    throw new Error("Enter a survey question between 1 and 500 characters.");
  const q = input.question.toLowerCase().replace(/\b([a-z]+)[’']s\b/g, "$1").replace(/[’']/g, "").replace(/&/g, " and ").replace(/\s+/g, " ");
  if (/https?:|localhost|\b(sql|select|drop|insert|employee|individual|salary|email|person|names)\b/.test(q))
    throw new Error("Only aggregate survey reporting is supported. Internal URLs, SQL and individual records are not allowed.");
  if (!/engagement|survey.*score|score.*survey|response rate|participation|formula/.test(q))
    throw new Error("Unsupported question. Ask about engagement, survey response rates, or the score formula.");
  const vocabulary = new Set(("what was were is are the everyone everyones company survey score scores at samsara over last three years year compare and in did engagement increase decrease between how calculated calculate formula response rate rates wide for human resources hr marketing engineering product sales customer success support department departments all of our us show me please vs versus from to through ytd point points changed change has it since much do does mean methodology defined definition explain work works 2024 2025 2026").split(" "));
  const unknown = (q.match(/[a-z0-9]+/g) || []).find(word => !vocabulary.has(word));
  if (unknown) throw new Error(`Unsupported year, department or topic: ${unknown}. Use 2024–2026 and ${allowedDepartments.join(", ")}.`);
  const requestedYears = [...new Set((q.match(/\b20\d{2}\b/g) || []).map(Number))].sort();
  let years = requestedYears.length ? requestedYears : allowedYears;
  if (/between|through|from/.test(q) && years.length === 2)
    years = allowedYears.filter(y => y >= years[0] && y <= years[years.length - 1]);
  const aliases: Record<string, string[]> = {
    "Human Resources": ["human resources", "hr"],
    "Marketing": ["marketing"],
    "Engineering & Product": ["engineering and product", "engineering", "product"],
    "Sales": ["sales"],
    "Customer Success & Support": ["customer success and support", "customer success", "customer support", "support"],
  };
  let departments = allowedDepartments.filter(d => aliases[d].some(alias => new RegExp(`\\b${alias}\\b`).test(q)));
  if (!departments.length) departments = allowedDepartments;
  if (input.filters !== undefined) {
    if (!input.filters || typeof input.filters !== "object" || Array.isArray(input.filters)) throw new Error("Invalid report filters.");
    const filters = input.filters as Record<string, unknown>;
    if (Object.keys(filters).some(k => !["years", "departments"].includes(k))) throw new Error("Unknown report filter.");
    if (filters.years !== undefined) {
      if (!Array.isArray(filters.years) || !filters.years.length || filters.years.some(y => !allowedYears.includes(y))) throw new Error("Years must be selected from 2024, 2025, 2026.");
      years = [...new Set(filters.years as number[])].sort();
    }
    if (filters.departments !== undefined) {
      if (!Array.isArray(filters.departments) || !filters.departments.length || filters.departments.some(d => !allowedDepartments.includes(d))) throw new Error(`Unknown department. Use ${allowedDepartments.join(", ")}.`);
      departments = allowedDepartments.filter(d => (filters.departments as string[]).includes(d));
    }
  }
  return { years, departments, metric: /formula|calculated|calculate|methodology|definition|defined/.test(q) ? "definition" : /response rate|participation/.test(q) ? "responseRate" : "engagement" };
}

export function filterPlan(input: unknown): Plan {
  return parseRequest({ question: "company survey score", filters: input });
}
