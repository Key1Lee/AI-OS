"use strict";
const $ = (id) => document.getElementById(id);
let accessToken = "";
let pending = false;

function textElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function appendMessage(text, kind) {
  $("welcome").classList.add("hidden");
  const message = textElement("div", text, "message " + kind);
  $("messages").append(message);
  message.scrollIntoView({ block: "nearest" });
  return message;
}

$("connect-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("connect").disabled = true;
  $("connection-status").textContent = "Connecting…";
  const token = $("token").value.trim();
  try {
    const response = await fetch("/me", { headers: { Authorization: "Bearer " + token } });
    if (!response.ok) throw new Error(response.status === 401 ? "That token was not recognized. Check access-tokens.json and try again." : "The service is unavailable. Please retry.");
    const data = await response.json();
    accessToken = token;
    $("token").value = "";
    $("identity-label").textContent = "Connected as " + data.identity.subject;
    $("identity-help").textContent = data.identity.region + " · " + data.identity.role + " · Policies matched to your access";
    $("mode").textContent = data.mode.includes("LLM: qwen_local") ? "Local Qwen connected" : data.mode.includes("LLM: mock") ? "Offline demo mode" : "Connected AI provider";
    $("connect-form").classList.add("hidden");
    $("disconnect").classList.remove("hidden");
    $("connection-status").textContent = "";
    $("question").focus();
  } catch (error) { $("connection-status").textContent = error.message; }
  finally { $("connect").disabled = false; }
});

$("disconnect").addEventListener("click", () => location.reload());
document.querySelectorAll("[data-question]").forEach((button) => button.addEventListener("click", () => {
  $("question").value = button.dataset.question;
  $("question").focus();
}));

$("question").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    if (!pending) $("question-form").requestSubmit();
  }
});

$("question-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (pending) return;
  if (!accessToken) {
    $("connection-status").textContent = "Connect your demo identity before asking a question.";
    $("token").focus();
    return;
  }
  const question = $("question").value.trim();
  if (question.length < 3) return;
  pending = true;
  $("send").disabled = true;
  appendMessage(question, "user");
  $("question").value = "";
  const waiting = appendMessage("Checking the policies available to you…", "assistant");
  try {
    const response = await fetch("/chat", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + accessToken }, body: JSON.stringify({ question }), signal: AbortSignal.timeout(55000) });
    if (!response.ok) throw new Error(response.status === 401 ? "Your access token is no longer valid. Disconnect and reconnect." : "The chat service is unavailable. Your question was not completed; please retry.");
    const result = await response.json();
    waiting.replaceChildren();
    const labels = { answered: "Found in your policies", abstained: "More evidence needed", escalated: "A person can help", refused: "Policy questions only", unavailable: "Temporarily unavailable" };
    waiting.append(textElement("span", labels[result.status] || result.status, "label " + result.status));
    waiting.append(textElement("div", result.answer, "answer"));
    for (const [index, citation] of result.citations.entries()) {
      const details = document.createElement("details");
      details.className = "citation";
      details.append(textElement("summary", `[${index + 1}] ${citation.title} · v${citation.version} · ${citation.section}`));
      details.append(textElement("p", citation.quote));
      details.append(textElement("small", `${citation.source} · Effective ${citation.effective_on} · Source ${citation.chunk_id.slice(0, 8)}`));
      waiting.append(details);
    }
    if (result.escalation) waiting.append(textElement("div", result.escalation, "handoff"));
  } catch (error) {
    waiting.className = "message error";
    waiting.textContent = error.name === "TimeoutError" ? "The request took too long. Please retry." : error.message;
  } finally {
    pending = false;
    $("send").disabled = false;
    waiting.scrollIntoView({ block: "nearest" });
    $("question").focus();
  }
});
