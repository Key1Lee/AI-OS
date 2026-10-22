import { readFile } from "node:fs/promises";
import path from "node:path";
import { projectRoot } from "./data";
import type { Reference } from "./types";

const documents = ["survey_questions.md", "engagement_score_definition.md", "data_quality_rules.md", "hr_reporting_privacy.md"];
export async function retrieve(question: string): Promise<Reference[]> {
  const terms = [...new Set(question.toLowerCase().match(/[a-z0-9]+/g) || [])].filter(t => t.length > 2);
  const ranked = await Promise.all(documents.map(async document => {
    const text = await readFile(path.join(projectRoot, "knowledge", document), "utf8");
    let relevance = terms.reduce((n, term) => n + (text.toLowerCase().includes(term) ? 1 : 0), 0);
    if (/calculat|formula|definition|engagement|score/.test(question.toLowerCase()) && document === "engagement_score_definition.md") relevance += 20;
    if (/questions|asked|wording|recommend|meaningful|retention/.test(question.toLowerCase()) && document === "survey_questions.md") relevance += 25;
    if (/why|caus|exclude|valid|duplicate/.test(question.toLowerCase()) && document === "data_quality_rules.md") relevance += 20;
    if (/response rate|participation/.test(question.toLowerCase()) && document === "data_quality_rules.md") relevance += 15;
    return { document, excerpt: text.split("\n").filter(l => !l.startsWith("#") && l.trim()).join("\n"), relevance };
  }));
  return ranked.sort((a, b) => b.relevance - a.relevance).slice(0, 3);
}
