const state = {
  config: null,
  session: null,
  timer: null,
  busy: false,
  pending: JSON.parse(localStorage.getItem("fdePendingSubmission") || "null"),
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    headers["X-Interview-Token"] = state.config?.request_token || "";
  }
  const response = await fetch(path, {
    ...options,
    headers,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 403 && payload.code === "local_token") {
      // Refresh the connection, but never silently replay a submitted answer.
      await loadConfiguration();
      payload.detail = "Connection refreshed after a restart. Retry the action or saved submission.";
    }
    const error = new Error(payload.detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

function requestId() {
  return `req_${crypto.randomUUID().replaceAll("-", "")}`;
}

function setBusy(busy) {
  state.busy = busy;
  document.querySelectorAll("button").forEach((button) => {
    if (!button.classList.contains("nav-button")) button.disabled = busy;
  });
  $("submitButton").textContent = busy ? "Evaluating…" : "Submit Answer";
}

function showToast(message) {
  $("toast").textContent = message;
  $("toast").classList.remove("hidden");
  window.setTimeout(() => $("toast").classList.add("hidden"), 5000);
}

function showError(message) {
  $("configBanner").textContent = message;
  $("configBanner").classList.remove("hidden");
}

function formatElapsed(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600).toString().padStart(2, "0");
  const minutes = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function renderSession(session) {
  state.session = session;
  localStorage.setItem("fdeCurrentSession", session.id);
  $("welcome").classList.add("hidden");
  $("exam").classList.remove("hidden");
  $("scenarioId").textContent = session.scenario_id;
  $("modeTag").textContent = session.mode === "ASSESSMENT" ? "ASSESSMENT MODE" : "MODULE REVIEW";
  $("scenarioTitle").textContent = session.scenario_title;
  $("scenarioText").textContent = session.scenario;
  $("questionText").textContent = session.current_question;
  $("sessionId").textContent = session.assessment_id;
  $("module").textContent = session.module;
  $("difficulty").textContent = `Level ${session.difficulty}`;
  $("turnNumber").textContent = session.turn_number;
  $("hintsUsed").textContent = session.hints_used;
  $("elapsed").textContent = formatElapsed(session.elapsed_seconds);
  $("competencies").replaceChildren(...session.competencies_in_scope.map(listItem));
  $("answerInput").value = localStorage.getItem(`fdeDraft:${session.id}`) || "";
  $("constraintsList").replaceChildren(...session.newly_introduced_constraints.map(listItem));
  $("constraintsBlock").classList.toggle("hidden", session.newly_introduced_constraints.length === 0);

  const active = session.status === "ACTIVE";
  $("answerPanel").classList.toggle("hidden", !active);
  $("reviewPanel").classList.toggle("hidden", session.status !== "MODULE_COMPLETE");
  if (session.status === "MODULE_COMPLETE") renderReview(session.module_review);
  if (session.last_error) showError(session.last_error);
  if (session.status === "PAUSED") {
    $("questionText").textContent = "Session paused. Resume when you are ready to continue.";
    renderResumeControl();
  }
  renderPending();
  startTimer(session);
}

function listItem(text) {
  const item = document.createElement("li");
  item.textContent = text;
  return item;
}

function renderReview(review) {
  const panel = $("reviewPanel");
  panel.replaceChildren();
  const title = document.createElement("h3");
  title.textContent = "Module evaluation";
  panel.append(title);
  const summary = document.createElement("p");
  summary.textContent = review.independent ? "Independent performance" : `Assisted performance (${review.assistance_level})`;
  panel.append(summary);
  const grid = document.createElement("div");
  grid.className = "review-grid";
  [
    ["Correctness", review.answer_correctness],
    ["Reasoning", review.reasoning_quality],
    ["Technical depth", review.technical_depth],
    ["Production awareness", review.production_awareness],
    ["Security", review.security_awareness],
    ["Testing", review.testing_quality],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "review-item";
    const key = document.createElement("span");
    key.textContent = label;
    const val = document.createElement("strong");
    val.textContent = value.replaceAll("_", " ");
    item.append(key, val);
    grid.append(item);
  });
  panel.append(grid);
  appendList(panel, "Evidence", review.evidence_observed);
  appendList(panel, "Independent strengths", review.strengths);
  appendList(panel, "Weaknesses", review.weaknesses);
  if (review.next_recommended_assessment) {
    const next = document.createElement("p");
    next.textContent = `Next: ${review.next_recommended_assessment}`;
    panel.append(next);
  }
  const button = document.createElement("button");
  button.className = "primary";
  button.textContent = "Continue Assessment";
  button.addEventListener("click", continueModule);
  panel.append(button);
  if (state.session?.last_error?.includes("evidence synchronization")) {
    const retry = document.createElement("button");
    retry.className = "secondary";
    retry.textContent = "Retry Evidence Sync";
    retry.addEventListener("click", retryEvidenceSync);
    panel.append(retry);
  }
}

function appendList(parent, titleText, items) {
  const title = document.createElement("h3");
  title.textContent = titleText;
  parent.append(title);
  const list = document.createElement("ul");
  (items.length ? items : ["None recorded."]).forEach((item) => list.append(listItem(item)));
  parent.append(list);
}

function renderResumeControl() {
  const panel = $("reviewPanel");
  panel.classList.remove("hidden");
  panel.replaceChildren();
  const button = document.createElement("button");
  button.className = "primary";
  button.textContent = "Resume Session";
  button.addEventListener("click", resumeSession);
  panel.append(button);
}

function renderPending() {
  const box = $("savedFailure");
  if (!state.pending || !state.session || state.pending.sessionId !== state.session.id) {
    box.classList.add("hidden");
    return;
  }
  box.replaceChildren();
  const text = document.createElement("span");
  text.textContent = "Your last submission was saved before the interviewer call failed. ";
  const retry = document.createElement("button");
  retry.className = "secondary";
  retry.textContent = "Retry saved submission";
  retry.addEventListener("click", retryPending);
  box.append(text, retry);
  box.classList.remove("hidden");
}

function startTimer(session) {
  if (state.timer) window.clearInterval(state.timer);
  const base = session.elapsed_seconds;
  const started = Date.now();
  state.timer = window.setInterval(() => {
    const increment = state.session?.status === "ACTIVE" ? Math.floor((Date.now() - started) / 1000) : 0;
    $("elapsed").textContent = formatElapsed(base + increment);
  }, 1000);
}

async function loadConfiguration() {
  state.config = await api("/api/config");
  if (!state.config.api_configured) {
    showError("OPENAI_API_KEY is not available to the local server. Export it in your environment, stop the server, and launch again. The key is never sent to this browser.");
    $("startButton").disabled = true;
  }
}

async function loadSessions() {
  const sessions = await api("/api/sessions");
  const list = $("sessionList");
  list.replaceChildren();
  sessions.slice(0, 5).forEach((session) => {
    const row = document.createElement("div");
    row.className = "session-row";
    const description = document.createElement("span");
    description.textContent = `${session.assessment_id} · ${session.module} · ${session.status}`;
    const button = document.createElement("button");
    button.className = "secondary";
    button.textContent = session.status === "PAUSED" ? "Resume" : "Open";
    button.addEventListener("click", async () => {
      const loaded = session.status === "PAUSED"
        ? await api(`/api/sessions/${session.id}/resume`, { method: "POST" })
        : await api(`/api/sessions/${session.id}`);
      renderSession(loaded);
    });
    row.append(description, button);
    list.append(row);
  });
}

async function startAssessment() {
  setBusy(true);
  try {
    const session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ target_role: "Senior Forward Deployed Engineer" }),
    });
    renderSession(session);
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(false);
  }
}

async function submit(kind, existing = null) {
  if (!state.session || state.busy) return;
  let content = existing ? existing.content : $("answerInput").value;
  if (kind === "hint" && !content.trim()) content = "I am requesting a hint.";
  if (kind !== "end_module" && !content.trim()) {
    showToast("Enter a response first.");
    return;
  }
  const pending = existing || {
    sessionId: state.session.id,
    requestId: requestId(),
    kind,
    content,
  };
  state.pending = pending;
  localStorage.setItem("fdePendingSubmission", JSON.stringify(pending));
  setBusy(true);
  try {
    const session = await api(`/api/sessions/${state.session.id}/submit`, {
      method: "POST",
      body: JSON.stringify({ request_id: pending.requestId, kind: pending.kind, content: pending.content }),
    });
    state.pending = null;
    localStorage.removeItem("fdePendingSubmission");
    $("answerInput").value = "";
    localStorage.removeItem(`fdeDraft:${state.session.id}`);
    renderSession(session);
  } catch (error) {
    showError(error.message);
    renderPending();
  } finally {
    setBusy(false);
  }
}

async function retryPending() {
  if (state.pending) await submit(state.pending.kind, state.pending);
}

async function pauseSession() {
  setBusy(true);
  try { renderSession(await api(`/api/sessions/${state.session.id}/pause`, { method: "POST" })); }
  catch (error) { showError(error.message); }
  finally { setBusy(false); }
}

async function resumeSession() {
  setBusy(true);
  try { renderSession(await api(`/api/sessions/${state.session.id}/resume`, { method: "POST" })); }
  catch (error) { showError(error.message); }
  finally { setBusy(false); }
}

async function continueModule() {
  setBusy(true);
  try {
    const session = await api(`/api/sessions/${state.session.id}/continue`, {
      method: "POST",
      body: JSON.stringify({ request_id: requestId() }),
    });
    renderSession(session);
  } catch (error) { showError(error.message); }
  finally { setBusy(false); }
}

async function retryEvidenceSync() {
  setBusy(true);
  try {
    renderSession(await api(`/api/sessions/${state.session.id}/sync`, { method: "POST" }));
    showToast("Evidence synchronized.");
  } catch (error) { showError(error.message); }
  finally { setBusy(false); }
}

async function loadDashboard() {
  const dashboard = await api("/api/dashboard");
  renderRows($("competencyDashboard"), dashboard.competencies, (item) => [item.competency, item.state]);
  renderRows($("weaknessDashboard"), dashboard.weaknesses, (item) => [item.competency, item.status]);
  renderRows($("historyDashboard"), dashboard.sessions, (item) => [`${item.assessment_id} · ${item.module}`, item.status]);
}

function renderRows(container, items, projector) {
  container.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "No evidence recorded.";
    container.append(empty);
    return;
  }
  items.forEach((item) => {
    const [label, value] = projector(item);
    const row = document.createElement("div");
    row.className = "progress-row";
    const text = document.createElement("span");
    text.textContent = label;
    const status = document.createElement("span");
    status.className = "state";
    status.textContent = value;
    row.append(text, status);
    container.append(row);
  });
}

document.querySelectorAll(".nav-button").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll(".nav-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    const dashboard = button.dataset.view === "dashboard";
    $("examView").classList.toggle("hidden", dashboard);
    $("dashboardView").classList.toggle("hidden", !dashboard);
    if (dashboard) await loadDashboard();
  });
});

$("startButton").addEventListener("click", startAssessment);
$("submitButton").addEventListener("click", () => submit("answer"));
$("clarifyButton").addEventListener("click", () => submit("clarification"));
$("hintButton").addEventListener("click", () => submit("hint"));
$("endModuleButton").addEventListener("click", () => submit("end_module"));
$("pauseButton").addEventListener("click", pauseSession);
$("refreshDashboard").addEventListener("click", loadDashboard);
$("answerInput").addEventListener("keydown", (event) => {
  if (event.metaKey && event.key === "Enter") {
    event.preventDefault();
    submit("answer");
  }
});
$("answerInput").addEventListener("input", () => {
  if (state.session) localStorage.setItem(`fdeDraft:${state.session.id}`, $("answerInput").value);
});

(async function initialize() {
  try {
    await loadConfiguration();
    await loadSessions();
    const previous = localStorage.getItem("fdeCurrentSession");
    if (previous) {
      try { renderSession(await api(`/api/sessions/${previous}`)); }
      catch { localStorage.removeItem("fdeCurrentSession"); }
    }
  } catch (error) {
    showError(`The local application could not initialize: ${error.message}`);
  }
})();
