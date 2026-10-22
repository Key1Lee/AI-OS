import { writeFileSync } from "node:fs";
import path from "node:path";
const groundedCode = `if($json.error || $json.validation?.status !== 'PASS' || !$json.report || !$json.ai) return [{json:{...$json,statusCode:$json.statusCode || ($json.validation?.status === 'FAIL' ? 409 : 502)}}];
return [{json:{...$json,orchestration:{mode:'n8n',executionId:$execution.id,workflowId:$workflow.id}}}];`;
const nodes: Record<string, unknown>[] = [];
function node(name: string, type: string, typeVersion: number, position: number[], parameters: unknown, extra = {}) {
  nodes.push({ id: name.toLowerCase().replaceAll(" ", "-"), name, type: `n8n-nodes-base.${type}`, typeVersion, position, parameters, ...extra });
}
node("Webhook", "webhook", 2, [0, 0], { httpMethod: "POST", path: "samsara-survey", responseMode: "responseNode", options: {} }, { webhookId: "d3258216-d83b-44cf-ab35-919a2c356273" });
node("Qwen Interpret Question", "httpRequest", 4.2, [220, 0], { method: "POST", url: "http://web:3000/api/assistant/interpret", sendBody: true, specifyBody: "json", jsonBody: "={{ JSON.stringify($json.body || {}) }}", options: { timeout: 35000, response: { response: { neverError: true, fullResponse: true } } } }, { onError: "continueErrorOutput" });
node("Interpretation Result", "code", 2, [440, 0], { jsCode: "const response=$json; const data=response.body || response; return [{json:{...data,question:$('Webhook').first().json.body.question,statusCode:response.statusCode >= 400 ? response.statusCode : undefined}}];" });
node("Valid Request", "if", 2.2, [660, 0], { conditions: { options: { caseSensitive: true, leftValue: "", typeValidation: "strict", version: 2 }, conditions: [{ id: "valid", leftValue: "={{ !!$json.plan && !$json.error }}", rightValue: "", operator: { type: "boolean", operation: "true", singleValue: true } }], combinator: "and" }, options: {} });
const httpOptions = { timeout: 10000 };
node("Mock Qualtrics", "httpRequest", 4.2, [880, -80], { url: "http://web:3000/api/mock-qualtrics/responses", options: httpOptions }, { onError: "continueErrorOutput" });
node("Metrics Engine", "httpRequest", 4.2, [1100, -80], { method: "POST", url: "http://web:3000/api/metrics", sendBody: true, specifyBody: "json", jsonBody: "={{ JSON.stringify({snapshot:{responses:$json.responses,headcount:$json.headcount},plan:$('Interpretation Result').first().json.plan}) }}", options: { ...httpOptions, response: { response: { neverError: true } } } }, { onError: "continueErrorOutput" });
node("RAG Retrieval", "httpRequest", 4.2, [1320, -80], { method: "POST", url: "http://web:3000/api/rag/search", sendBody: true, specifyBody: "json", jsonBody: "={{ JSON.stringify({question:$('Interpretation Result').first().json.retrievalQuery}) }}", options: httpOptions }, { onError: "continueErrorOutput" });
node("Qwen Grounded Answer", "httpRequest", 4.2, [1540, -80], { method: "POST", url: "http://web:3000/api/assistant/answer", sendBody: true, specifyBody: "json", jsonBody: "={{ JSON.stringify({question:$('Interpretation Result').first().json.question,interpretation:$('Interpretation Result').first().json,metrics:$('Metrics Engine').first().json,references:$json.references}) }}", options: { timeout: 35000, response: { response: { neverError: true, fullResponse: true } } } }, { onError: "continueErrorOutput" });
node("Build Grounded Answer", "code", 2, [1760, -80], { jsCode: "const response=$json; const data=response.body || response; return [{json:{...data,statusCode:response.statusCode >= 400 ? response.statusCode : undefined}}];" });
node("Attach Execution Receipt", "code", 2, [1980, -80], { jsCode: groundedCode });
node("Handle Failure", "code", 2, [1100, 230], { jsCode: "const statusCode = $json.statusCode || 502; return [{json:{error:$json.error && typeof $json.error === 'string' ? $json.error : 'A workflow service failed. Check mock data, reference validation and execution logs.',statusCode,validation:{status:'NOT VERIFIED'},orchestration:{mode:'n8n',executionId:$execution.id,workflowId:$workflow.id}}}];" });
node("Respond to Webhook", "respondToWebhook", 1.4, [2200, 0], { respondWith: "json", responseBody: "={{ $json }}", options: { responseCode: "={{ $json.statusCode || 200 }}" } });
const connections: Record<string, unknown> = {};
function connect(from: string, outputs: string[][]) {
  connections[from] = { main: outputs.map(names => names.map(name => ({ node: name, type: "main", index: 0 }))) };
}
connect("Webhook", [["Qwen Interpret Question"]]);
connect("Qwen Interpret Question", [["Interpretation Result"], ["Handle Failure"]]);
connect("Interpretation Result", [["Valid Request"]]);
connect("Valid Request", [["Mock Qualtrics"], ["Handle Failure"]]);
connect("Mock Qualtrics", [["Metrics Engine"], ["Handle Failure"]]);
connect("Metrics Engine", [["RAG Retrieval"], ["Handle Failure"]]);
connect("RAG Retrieval", [["Qwen Grounded Answer"], ["Handle Failure"]]);
connect("Qwen Grounded Answer", [["Build Grounded Answer"], ["Handle Failure"]]);
connect("Build Grounded Answer", [["Attach Execution Receipt"]]);
connect("Attach Execution Receipt", [["Respond to Webhook"]]);
connect("Handle Failure", [["Respond to Webhook"]]);
writeFileSync(path.resolve("../n8n/qualtrics-survey-demo.json"), JSON.stringify({
  id: "samsaraSurveyDemo2026", name: "Samsara People Analytics — Synthetic Demo", active: false,
  versionId: "c5148854-369b-4560-b832-2c56a49d1d32", nodes, connections,
  settings: { executionOrder: "v1", saveDataSuccessExecution: "all", saveDataErrorExecution: "all", executionTimeout: 90 },
  pinData: {}, tags: [],
}, null, 2) + "\n");
console.log("Generated native n8n workflow with local Qwen interpretation and grounded evidence selection.");
