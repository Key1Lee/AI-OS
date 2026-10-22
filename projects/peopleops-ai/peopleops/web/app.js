"use strict";
const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pretty = value => String(value).replaceAll("_", " ");
const badge = (value, label = pretty(value)) => `<span class="tag ${esc(value)}">${esc(label)}</span>`;
const dateLabel = value => new Date(value).toLocaleDateString("en-US", {month:"short",day:"numeric",timeZone:"Asia/Seoul"});
const fullDate = () => new Date().toLocaleDateString("en-US", {month:"long",day:"numeric",year:"numeric",timeZone:"Asia/Seoul"});
const state = {view:"overview", identities:[], user:null, token:"", requests:[], employees:[], tasks:[], policies:[], filter:"", page:0, sequence:0};
let toastTimer;
function toast(message, error=false) { const box=$("#toast"); box.textContent=message; box.className=error?"error":""; box.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>box.hidden=true,6500); }
async function api(path, options={}) {
  const {acceptFailure=false,...rest}=options;
  const response=await fetch(path,{...rest,headers:{"Authorization":`Bearer ${state.token}`,"Content-Type":"application/json",...(rest.headers||{})}});
  const body=await response.json();
  if(!response.ok && !acceptFailure) throw new Error(typeof body.detail==="string"?body.detail:body.error_code||`Request failed (${response.status}). Check the submitted fields.`);
  return body;
}
const post = (path, body={},options={}) => api(path,{method:"POST",body:JSON.stringify(body),...options});
const patch = (path, body) => api(path,{method:"PATCH",body:JSON.stringify(body)});
function heading(kicker,title,subtitle,action="") { return `<div class="page-heading"><div><p class="eyebrow">${esc(kicker)}</p><h1>${esc(title)}</h1><p class="subtext">${esc(subtitle)}</p></div>${action}</div>`; }
function card(title,subtitle,body,action="") { return `<section class="card"><div class="card-head"><div><h2>${esc(title)}</h2>${subtitle?`<p>${esc(subtitle)}</p>`:""}</div>${action}</div>${body}</section>`; }
function stat(label,value,foot,symbol="↗") { return `<article class="stat"><div class="stat-label">${esc(label)}<span class="stat-symbol">${symbol}</span></div><div class="stat-value">${esc(value)}</div><div class="stat-foot">${foot}</div></article>`; }
const empty = text => `<div class="empty">${esc(text)}</div>`;
function table(headers,body) { return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`; }
function requestRows(items,compact=false) { return items.map(r=>`<tr><td><button class="text-button" data-action="request-detail" data-id="${esc(r.request_id)}">${esc(r.subject)}</button><span class="id">${esc(r.request_id)}</span></td>${compact?"":`<td><strong>${esc(r.full_name)}</strong><span class="id">${esc(r.employee_id)}</span></td>`}<td>${esc(r.team)}</td><td>${badge(r.status)}</td><td>${dateLabel(r.created_at)}</td></tr>`).join(""); }
function flow() { return `<div class="flow">${[["W","Workday mock","Fictional source"],["⇄","Python ETL","Clean & quarantine"],["▤","SQLite + dbt","Store & validate"],["✳","Policy retrieval","Permission + citation"],["↗","HR workflows","Route & notify"]].map((x,i)=>`${i?'<span class="flow-arrow">→</span>':""}<div class="flow-step"><span>${x[0]}</span><div>${x[1]}<small>${x[2]}</small></div></div>`).join("")}</div>`; }

async function overview() {
  if(state.user.role==="employee") {
    const [person,requests,tasks]=await Promise.all([api(`/api/employees/${state.user.employee_id}`),api("/api/requests"),api("/api/onboarding")]);
    state.requests=requests; state.tasks=tasks;
    return heading("YOUR PEOPLE WORKSPACE",`Hello, ${person.full_name.split(" ")[0]}.`,"Your requests, onboarding, and approved company policies.",'<button class="btn" data-action="new-request">＋ New HR request</button>')+
      `<div class="stats">${stat("Your unresolved requests",requests.filter(r=>r.status!=="resolved").length,"Visible to you and HR","▤")}${stat("Your onboarding tasks",tasks.filter(t=>t.status==="pending").length,"Tasks awaiting completion","✓")}${stat("Your department",person.department,"Fictional employee profile","♧")}${stat("Policy support","Available","Cited answers from approved policies","✳")}</div>`+
      card("Your HR requests","Only requests linked to your employee identity",requests.length?table(["Request","Routed to","Status","Submitted"],requestRows(requests,true)):empty("You have no HR requests."))+
      `<div class="section-space">${card("How this workspace works","Follow one request from source to notification",flow())}</div>`;
  }
  const m=await api("/api/metrics");
  let ops=null, requests=[];
  if(state.user.role==="hr") [ops,requests]=await Promise.all([api("/api/ops"),api("/api/requests")]);
  state.requests=requests; $("#request-count").textContent=String(m.unresolved_requests);
  const max=Math.max(1,...m.departments.map(d=>d.headcount));
  const bars=`<div class="card-body">${m.departments.map(d=>`<div class="dept-row"><span>${esc(d.department)}</span><div class="bar-track"><div class="bar-fill" style="width:${d.headcount/max*100}%"></div></div><strong>${d.headcount}</strong></div>`).join("")}<p class="subtext" style="margin-top:22px;font-size:9px">Active employees and employees on leave · excludes prehires and departures</p></div>`;
  const colors=["#067762","#83ad91","#b8cfa4","#d5e1c4","#63876f","#a4bca0"];
  let position=0;
  const segments=m.request_categories.map((c,i)=>{const start=position;position+=c.count/Math.max(1,m.unresolved_requests)*100;return `${colors[i%colors.length]} ${start}% ${position}%`;});
  const counts=`<div class="card-body"><div class="donut-area"><div class="ring" style="background:conic-gradient(${segments.join(",")||"#e8eee0 0% 100%"})"><div><strong>${m.unresolved_requests}</strong><small>unresolved</small></div></div><div class="legend">${m.request_categories.map((c,i)=>`<div><i style="background:${colors[i%colors.length]}"></i>${esc(pretty(c.category))}<strong>${c.count}</strong></div>`).join("")}</div></div></div>`;
  return heading("PEOPLE OPERATIONS, CONNECTED","A clearer view of your people.","One place for workforce insights, HR support, and reliable workflows.",`<span class="date-chip">◷ ${fullDate()}</span>`)+
    `<div class="banner"><span>✳</span><span><strong>Your engineering lab is ready.</strong> Explore a fictional HR operation from raw employee records to cited policy answers.</span><span class="tag green">LOCAL SIMULATION</span></div>`+
    `<div class="stats">${stat("Current headcount",m.headcount.toLocaleString(),`<strong>${m.on_leave} on leave</strong> · ${m.prehires} upcoming hire`,"♧")}${stat("New hires",m.new_hires_30d,`<strong>Last 30 days</strong> · ${m.departures_30d} departure`,"↗")}${stat("Unresolved requests",m.unresolved_requests,`${m.resolved_requests} resolved · ${m.total_requests} total requests`,"▤")}${stat("Onboarding complete",m.onboarding_completion_pct+"%",`${m.completed_tasks} of ${m.total_tasks} tasks completed`,"✓")}</div>`+
    `<div class="grid-two">${card("Headcount by department","Current workforce distribution",bars,badge("green",m.records+" validated records"))}${card("HR request workload","Unresolved requests by category",counts,'<button class="text-button" data-view="requests">View queue ↗</button>')}</div>`+
    (state.user.role==="hr"?card("Requests needing attention","Review, route, and resolve employee questions",table(["Request","Employee","Routed to","Status","Submitted"],requestRows(requests.filter(r=>r.status!=="resolved").slice(0,4))),'<button class="text-button" data-view="requests">All requests →</button>'):"" )+
    `<div class="section-space">${card("From source to service","A small system with an inspectable path through every stage",flow(),ops?badge(ops.freshness.state==="fresh"?"green":"amber",ops.freshness.state==="fresh"?"Source data fresh":"Check source freshness"):badge("green","Aggregate access"))}</div>`;
}

async function requestsView() {
  state.requests=await api("/api/requests"+(state.filter?`?status=${state.filter}`:""));
  return heading("EMPLOYEE SUPPORT","HR requests","Every question has an owner, a status, and a next step.",'<button class="btn" data-action="new-request">＋ New HR request</button>')+
    `<div class="toolbar"><input id="request-search" placeholder="Search loaded requests…" aria-label="Search requests"><select id="request-filter" aria-label="Filter request status"><option value="">All statuses</option>${["open","in_progress","resolved"].map(v=>`<option value="${v}" ${state.filter===v?"selected":""}>${pretty(v)}</option>`).join("")}</select><span class="subtext">${state.requests.length} requests · latest 200</span></div>`+
    card("Request queue","Descriptions stay in the secure queue; notifications contain identifiers only.",`<div id="request-table">${state.requests.length?table(["Request","Employee","Routed to","Status","Submitted"],requestRows(state.requests)):empty("No requests match this status.")}</div>`);
}

async function people() {
  const hr=state.user.role==="hr";
  const [directory,tasks]=await Promise.all([hr?api(`/api/employees?limit=100&offset=${state.page*100}`):api(`/api/employees/${state.user.employee_id}`),api("/api/onboarding")]);
  state.tasks=tasks;
  const peopleHTML=hr?table(["Employee","Department","Status","Start date"],directory.items.map(e=>`<tr><td><strong>${esc(e.full_name)}</strong><span class="id">${esc(e.employee_id)} · ${esc(e.email)}</span></td><td>${esc(e.department)}</td><td>${badge(e.status)}</td><td>${esc(e.hire_date)}</td></tr>`).join("")):
    `<div class="card-body profile"><span class="avatar">${esc(directory.full_name.split(" ").map(x=>x[0]).join(""))}</span><div><h2>${esc(directory.full_name)}</h2><p class="subtext">${esc(directory.employee_id)} · ${esc(directory.department)}<br>${esc(directory.email)} · ${esc(directory.status)}</p></div></div>`;
  return heading("PEOPLE & ONBOARDING",hr?"A thoughtful start for every hire.":"Your employee workspace.",hr?"Validated employee records and onboarding tasks in one place.":"Your own employee record and assigned onboarding tasks.")+
    card(hr?"Employee directory":"Your profile",hr?`${directory.total} validated records · page ${state.page+1}`:"Your profile is visible to you and HR.",peopleHTML,
      hr?`<div><button class="btn tiny secondary" data-action="people-prev" ${state.page===0?"disabled":""}>←</button> <button class="btn tiny secondary" data-action="people-next" ${(state.page+1)*100>=directory.total?"disabled":""}>→</button></div>`:"")+
    `<div class="page-heading section-space"><div><h2>Onboarding checklist</h2><p class="subtext">${tasks.filter(t=>t.status==="completed").length} of ${tasks.length} displayed tasks complete · latest 300</p></div>${hr?'<button class="btn secondary" data-action="new-hire">＋ Simulate a new hire</button>':""}</div>`+
    `<div class="task-list">${tasks.map(t=>`<article class="task-card">${badge(t.status)}<h3>${esc(t.kind)}</h3><p>${esc(t.full_name)} · ${esc(t.employee_id)}<br>Owner: ${esc(t.owner_team)}<br>Due ${esc(t.due_date)}</p><button class="btn tiny secondary" data-action="task-toggle" data-id="${esc(t.task_id)}">${t.status==="completed"?"Reopen task":"Mark complete"}</button></article>`).join("")||empty("No onboarding tasks are assigned yet.")}</div>`;
}

async function assistant() {
  state.policies=await api("/api/policies");
  return `<div class="assistant-layout"><div class="assistant-hero"><div class="spark">✳</div><p class="eyebrow">APPROVED POLICIES. CLEAR ANSWERS.</p><h1>A little clarity for your workday.</h1><p class="subtext">Ask about payroll, time off, benefits, or onboarding.<br>Every supported answer comes with its source.</p></div><form id="assistant-form" class="assistant-form"><input id="question" name="question" required minlength="3" maxlength="500" aria-label="Your policy question" placeholder="For example, when is payroll paid?"><button class="btn" type="submit">Ask assistant ↗</button></form><p class="privacy-line">Local extractive retrieval · No live LLM · Please leave personal and financial details out.</p><div class="prompts">${["When is payroll paid?","How much vacation do I get?","What are my onboarding tasks?"].map(q=>`<button class="prompt" data-action="prompt" data-question="${esc(q)}">${esc(q)}</button>`).join("")}</div><div id="answer-area" aria-live="polite"></div><div class="divider"></div><h2>Your policy library</h2><p class="subtext">${state.policies.length} available policies for your current role.</p><div class="policy-grid">${state.policies.map(p=>`<article class="policy-card">${badge(p.visibility==="hr"?"amber":"green",p.visibility==="hr"?"HR ONLY":"COMPANY POLICY")}<h3 style="margin-top:14px">${esc(p.title)}</h3><p>${esc(p.body.slice(0,100))}…</p><button class="text-button" data-action="policy-detail" data-id="${esc(p.policy_id)}">Read policy ↗</button></article>`).join("")||empty("The policy library is currently unavailable. Please contact HR.")}</div></div>`;
}

async function operationsView() {
  const [ops,notifications,audits]=await Promise.all([api("/api/ops"),api("/api/notifications"),api("/api/audit")]);
  const latest=ops.runs[0];
  return heading("RELIABILITY & TRUST","See the signals. Practice recovery.","Inspect quality, simulate integration failures, and follow the evidence.",'<button class="btn secondary" data-action="refresh">↻ Refresh signals</button>')+
    `<div class="stats">${stat("Source freshness",ops.freshness.state,`${ops.freshness.source_age_hours??"—"} hours since source update`,"◷")}${stat("HTTP availability",ops.http.availability_pct===null?"—":ops.http.availability_pct+"%",`${ops.http.sample_size} requests · last 1,000 at most`,"⌁")}${stat("Response time, p95",ops.http.p95_ms===null?"—":ops.http.p95_ms+" ms","Observed local HTTP requests","↗")}${stat("Latest pipeline",latest?.status||"No run",`${latest?.duration_ms??"—"} ms · ${latest?.attempts??0} HTTP attempts`,"⇄")}</div>`+
    `<div class="grid-two">${card("Data quality checks","Detection is separate from cleaning.",`<div class="card-body checks">${ops.quality.map(c=>`<div class="check"><span>${c.passed?"✓":"!"}</span>${esc(c.name)}<span class="result">${badge(c.passed?"green":"red",c.passed?"PASS":"FAIL")}</span></div>`).join("")}</div>`)}${card("Failure playground","Simulations change only this local database.",`<div class="card-body"><div class="ops-controls"><select id="scenario" aria-label="Pipeline scenario">${[["normal","Healthy source"],["transient","Two API failures, then recovery"],["unavailable","Workday unavailable"],["stale","Stale employee data"],["new_hire","One new hire"],["duplicate","Duplicate source records"],["growth","About 5,000 source rows"],["malformed","Invalid API response"]].map(([v,l])=>`<option value="${v}">${l}</option>`).join("")}</select><button class="btn" data-action="run-scenario">Run simulation</button></div><div class="divider"></div><div class="ops-controls"><button class="btn secondary tiny" data-action="queue-reminders">Queue overdue reminders</button><button class="btn secondary tiny" data-action="deliver">Deliver notifications</button><button class="btn secondary tiny" data-action="fail-slack">Fail next Slack delivery</button></div><div class="ops-controls" style="margin-top:12px"><button class="text-button" data-action="hide-knowledge">Simulate missing policies</button><button class="text-button" data-action="restore-knowledge">Restore policies</button></div><div id="operation-result" class="result-box">${latest?`${latest.received} source rows → ${latest.accepted} accepted + ${latest.rejected} rejected + ${latest.duplicates} duplicates`:"No pipeline results."}\n${ops.quarantine.map(q=>`${q.reason}: ${q.count}`).join("\n")}</div></div>`)}</div>`+
    card("Pipeline history","Failed fetches preserve the last successful employee state.",table(["Scenario","Status","Rows","Changed","Rejected / duplicates","Duration"],ops.runs.map(r=>`<tr><td><strong>${esc(pretty(r.scenario))}</strong><span class="id">${esc(r.started_at)}</span></td><td>${badge(r.status)}</td><td>${r.received}</td><td>${r.changed}</td><td>${r.rejected} / ${r.duplicates}</td><td>${r.duration_ms??"—"} ms</td></tr>`).join("")))+
    `<div class="grid-two section-space">${card("Mock Slack","Identifier-only messages; nothing is sent to Slack.",`<div class="card-body">${notifications.slice(0,6).map(n=>`<div class="notification"><span class="tag green">${esc(n.channel)}</span><p>${esc(n.text)}</p><small>${esc(n.created_at)}</small></div>`).join("")||empty("No messages delivered yet.")}<p class="subtext" style="margin-top:15px">Outbox: ${ops.outbox.map(o=>`${o.count} ${o.status}`).join(" · ")}</p></div>`)}${card("Audit trail","Actions and outcomes, without confidential request text.",table(["Actor / action","Outcome"],audits.slice(0,8).map(a=>`<tr><td><strong>${esc(a.actor)}</strong><span class="id">${esc(a.action)} · ${esc(a.target)}</span></td><td>${badge(a.outcome==="allowed"?"green":"red",a.outcome)}</td></tr>`).join("")))}</div>`;
}

async function learn() {
  const lessons=await (await fetch("/static/lessons.json")).json();
  let done=[]; try{done=JSON.parse(localStorage.getItem("peopleops-lessons")||"[]");}catch{}
  return heading("BUILD IT. EXPLAIN IT. OPERATE IT.","Your engineering learning path.","Twelve small phases connect the code to the business problem.",`<span class="learning-progress">${done.length} / 12 self-reviewed</span>`)+
    '<div class="notice">The application is built. Your understanding is a separate journey: complete the starter exercises, run the checks, and explain the result in your own words. Checkmarks record your own review; they are not an assessment score.</div>'+
    lessons.map((l,i)=>`<details class="lesson"><summary><span class="lesson-num">${String(i+1).padStart(2,"0")}</span>${esc(l.title)}<small>${esc(l.file)}</small></summary><div class="lesson-content"><p><strong>Business problem:</strong> ${esc(l.business)}</p><p><strong>Visual:</strong> ${esc(l.before)} → ${esc(l.after)}</p><p><strong>Our task:</strong> ${esc(l.task)}</p><p><strong>Code:</strong></p><pre>${esc(l.starter)}</pre><p><strong>Explanation:</strong> ${esc(l.explanation)}</p><p><strong>How to verify:</strong></p><pre>${esc(l.command)}\n# Expected: ${esc(l.expected)}</pre><p><strong>Your turn:</strong> ${esc(l.question)}</p><label class="check-lesson"><input type="checkbox" data-lesson="${i}" ${done.includes(i)?"checked":""}> I reviewed this phase and ran its check.</label></div></details>`).join("");
}

const views={overview,requests:requestsView,people,assistant,operations:operationsView,learn};
const names={overview:"Overview",requests:"HR requests",people:"People & onboarding",assistant:"Policy assistant",operations:"System health",learn:"Learning path"};
async function render(view=state.view) {
  state.view=view; const sequence=++state.sequence;
  $("#breadcrumb").textContent=names[view];
  document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
  $("#main").innerHTML=empty("Loading your workspace…");
  try { const content=await views[view](); if(sequence!==state.sequence)return; $("#main").innerHTML=content; }
  catch(error){if(sequence!==state.sequence)return; $("#main").innerHTML=heading("WORKSPACE",names[view],error.message)+empty("Select another workspace page or refresh to try again.");toast(error.message,true);}
}
function modal(html){$("#dialog-content").innerHTML=html;$("#dialog").showModal();}
const modalHead=title=>`<div class="dialog-head"><h2>${esc(title)}</h2><button class="close" data-action="close" aria-label="Close dialog">×</button></div>`;

async function newRequest(){
  if(state.user.role==="analyst")return;
  let employeeField="";
  if(state.user.role==="hr") {
    const directory=await api("/api/employees?limit=200");
    employeeField=`<label class="field">Employee<select name="employee_id">${directory.items.map(e=>`<option value="${esc(e.employee_id)}">${esc(e.full_name)} · ${esc(e.employee_id)}</option>`).join("")}</select></label>`;
  }
  modal(modalHead("New HR request")+`<p class="subtext">Describe the issue. Leave bank details and identity documents out.</p><form id="request-form">${employeeField}<label class="field">Subject<input name="subject" required minlength="3" maxlength="120" placeholder="For example, payroll help"></label><label class="field">What do you need help with?<textarea name="description" required minlength="5" maxlength="2000" placeholder="Give HR a short description of the issue."></textarea></label><label class="field">Priority<select name="priority"><option value="normal">Normal</option><option value="high">High</option></select></label><div class="dialog-actions"><button type="button" class="btn secondary" data-action="close">Cancel</button><button type="submit" class="btn">Submit request ↗</button></div></form>`);
  $("#request-form").dataset.key=crypto.randomUUID();
}

async function showRequest(id){
  const r=state.requests.find(x=>x.request_id===id); if(!r)return;
  modal(modalHead(r.subject)+`<p class="subtext">${esc(r.request_id)} · ${esc(r.full_name)} · ${esc(r.employee_id)}</p><div class="meta-row">${badge(r.status)}${badge("",r.category)}${badge("",r.team)}</div><p class="detail-text">${esc(r.description)}</p><p class="subtext">Routing: ${r.routing_confidence?"rule match":"human triage"} · Submitted ${dateLabel(r.created_at)}</p>`+(state.user.role==="hr"?`<div class="divider"></div><label class="field">Request status<select id="detail-status">${["open","in_progress","resolved"].map(v=>`<option value="${v}" ${v===r.status?"selected":""}>${pretty(v)}</option>`).join("")}</select></label><div class="dialog-actions"><button class="btn" data-action="save-request" data-id="${esc(id)}">Save status</button></div>`:""));
}

async function ask(question){
  const input=$("#question");input.value=question;
  const button=$("#assistant-form button");button.disabled=true;
  $("#answer-area").innerHTML=empty("Finding an approved policy passage…");
  try { const result=await post("/api/assistant",{question});
    $("#answer-area").innerHTML=`<article class="answer"><div class="meta-row">${badge(result.escalated?"amber":"green",result.escalated?"HR REVIEW RECOMMENDED":"SUPPORTED BY POLICY")}${badge("","EXTRACTIVE RETRIEVAL")}</div><p>${esc(result.answer)}</p>${result.citations.map(c=>`<div class="citation"><span>▧</span><button class="text-button" data-action="policy-detail" data-id="${esc(c.policy_id)}">${esc(c.title)} · v${c.version} ↗</button><span class="right muted">${esc(c.policy_id)}</span></div>`).join("")}${result.escalated&&state.user.role!=="analyst"?'<button class="btn secondary tiny" data-action="new-request">Create an HR request →</button>':""}</article>`;
  }catch(error){toast(error.message,true);$("#answer-area").innerHTML=empty("The assistant could not complete the request. Please try again.");}
  finally{button.disabled=false;}
}

async function runScenario(scenario){
  const result=await post("/api/ops/pipeline",{scenario},{acceptFailure:true});
  await render();
  if($("#operation-result"))$("#operation-result").textContent=JSON.stringify(result,null,2);
  toast(result.status==="failed"?`Simulated failure: ${result.error_code}. Prior employee state preserved.`:`Pipeline complete: ${result.changed} changed, ${result.rejected} rejected, ${result.duplicates} duplicates.`,result.status==="failed");
}

document.addEventListener("click",async event=>{
  const viewButton=event.target.closest("[data-view]");
  if(viewButton){await render(viewButton.dataset.view);return;}
  const button=event.target.closest("[data-action]");if(!button)return;
  const action=button.dataset.action;
  try{
    if(action==="close"){$("#dialog").close();return;}
    if(action==="new-request"){await newRequest();return;}
    if(action==="request-detail"){await showRequest(button.dataset.id);return;}
    if(action==="save-request"){await patch(`/api/requests/${button.dataset.id}`,{status:$("#detail-status").value});$("#dialog").close();toast("Request status updated.");await render();return;}
    if(action==="task-toggle"){const task=state.tasks.find(t=>t.task_id===button.dataset.id);await patch(`/api/onboarding/${task.task_id}`,{status:task.status==="completed"?"pending":"completed"});toast("Onboarding task updated.");await render();return;}
    if(action==="policy-detail"){const p=await api(`/api/policies/${button.dataset.id}`);modal(modalHead(p.title)+`<div class="meta-row">${badge("green",p.visibility==="hr"?"HR ONLY":"COMPANY POLICY")}${badge("",`Version ${p.version}`)}</div><p class="detail-text">${esc(p.body)}</p><p class="subtext">${esc(p.policy_id)} · Fictional learning policy</p>`);return;}
    if(action==="prompt"){await ask(button.dataset.question);return;}
    if(action==="refresh"){await render();return;}
    if(action==="people-next"){state.page++;await render();return;}
    if(action==="people-prev"){state.page=Math.max(0,state.page-1);await render();return;}
    button.disabled=true;
    if(action==="run-scenario")await runScenario($("#scenario").value);
    if(action==="new-hire")await runScenario("new_hire");
    if(action==="queue-reminders"){const r=await post("/api/ops/reminders");toast(`${r.queued} new reminders queued; repeated events are deduplicated.`);await render();}
    if(action==="deliver"){const r=await post("/api/ops/deliver");toast(`${r.sent} notifications delivered, ${r.failed} failed.`);await render();}
    if(action==="fail-slack"){await post("/api/ops/reminders");const r=await post("/api/ops/deliver",{failures:1500});toast(`${r.failed} notifications failed after retries. Use Deliver notifications to recover.`);await render();}
    if(action==="hide-knowledge"||action==="restore-knowledge"){const available=action==="restore-knowledge";await post("/api/ops/knowledge",{available});toast(available?"Policy documents restored.":"Policies unavailable. The assistant will now escalate.");}
  }catch(error){toast(error.message,true);}finally{button.disabled=false;}
});

document.addEventListener("submit",async event=>{
  if(event.target.id==="assistant-form"){event.preventDefault();await ask($("#question").value);}
  if(event.target.id==="request-form"){
    event.preventDefault();const form=event.target,button=$("button[type=submit]",form);button.disabled=true;
    try{const payload=Object.fromEntries(new FormData(form));const result=await post("/api/requests",payload,{headers:{"Idempotency-Key":form.dataset.key}});$("#dialog").close();toast(`Request ${result.request.request_id} routed to ${result.request.team}.`);await render("requests");}catch(error){toast(error.message,true);}finally{button.disabled=false;}
  }
});
document.addEventListener("input",event=>{
  if(event.target.id==="request-search"){
    const query=event.target.value.toLowerCase();const filtered=state.requests.filter(r=>(r.subject+" "+r.full_name+" "+r.request_id+" "+r.team).toLowerCase().includes(query));
    $("#request-table").innerHTML=filtered.length?table(["Request","Employee","Routed to","Status","Submitted"],requestRows(filtered)):empty("No matching requests.");
  }
});
document.addEventListener("change",async event=>{
  if(event.target.id==="identity")await setIdentity(event.target.value);
  if(event.target.id==="request-filter"){state.filter=event.target.value;await render();}
  if(event.target.dataset.lesson!==undefined){let done=[];try{done=JSON.parse(localStorage.getItem("peopleops-lessons")||"[]");}catch{}const id=Number(event.target.dataset.lesson);done=done.filter(x=>x!==id);if(event.target.checked)done.push(id);localStorage.setItem("peopleops-lessons",JSON.stringify(done));$(".learning-progress").textContent=`${done.length} / 12 self-reviewed`;}
});
async function setIdentity(id){
  const identity=state.identities.find(i=>i.principal_id===id)||state.identities[0];
  state.token=identity.token;state.user=identity;state.page=0;state.requests=[];state.tasks=[];
  sessionStorage.setItem("peopleops-identity",identity.principal_id);$("#identity").value=identity.principal_id;$("#identity-avatar").textContent=identity.role==="hr"?"HR":identity.label.split(" ").map(x=>x[0]).join("").slice(0,2);
  $("#request-count").textContent="";
  document.querySelectorAll("#nav [data-view]").forEach(b=>b.hidden=identity.role==="analyst"?["requests","people","operations"].includes(b.dataset.view):identity.role==="employee"&&b.dataset.view==="operations");
  await render("overview");
}
async function boot(){
  try{
    const response=await fetch("/api/demo/identities");
    if(!response.ok)throw new Error("Demo switching is disabled. Use a locally provisioned Bearer token with the API explorer.");
    state.identities=await response.json();
    $("#identity").innerHTML=state.identities.map(i=>`<option value="${esc(i.principal_id)}">${esc(i.label)} · ${esc(i.role)}</option>`).join("");
    $("#footer-status").textContent="Local service connected";
    await setIdentity(sessionStorage.getItem("peopleops-identity")||"hr");
  }catch(error){$("#main").innerHTML=empty(error.message);$("#footer-status").textContent="Service unavailable";}
}
boot();
