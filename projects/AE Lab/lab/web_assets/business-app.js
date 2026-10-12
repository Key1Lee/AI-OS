'use strict';
function showCatalog(){
  if(busy){notice('Wait for the current operation to finish before choosing an exercise.');return;}
  $('catalog-list').innerHTML=catalog.map(c=>`<button class="catalog-card" data-case="${esc(c.id)}"><span class="eyebrow">${String(c.number).padStart(2,'0')} · ${esc(c.sector)} · ${esc(c.priority)}</span><strong>${esc(c.title)}</strong><span>${esc(c.concept)}</span><b>Start this business problem →</b></button>`).join('')+`<button class="catalog-card original" data-case="ORCH-IDEMPOTENCY-001"><span class="eyebrow">ORIGINAL EXERCISE</span><strong>Partial write + retry</strong><span>Keep practicing the original integrated retry-safety lab.</span><b>Start the original exercise →</b></button>`;
  document.querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>newSession(button.dataset.case)));
  $('catalog-dialog').showModal();
}
function businessMetrics(phase){
  if(!phase)return '';
  return `<div class="metrics"><div class="metric"><small>OUTPUT ROWS</small><strong>${count(phase.row_count)}</strong><em>expected ${count(phase.expected_count)}</em></div><div class="metric ${phase.model_status==='FAIL'?'warn':''}"><small>${esc(phase.metric_label)}</small><strong>${count(phase.value)}</strong><em>expected ${count(phase.expected_value)}</em></div><div class="metric"><small>PUBLICATION</small><strong class="gate-value">${phase.publication==='BLOCKED'?'Blocked':'Eligible'}</strong><em>all business checks required</em></div></div><div class="status-row"><span>SQL: executed</span><span class="${phase.model_status==='FAIL'?'bad':''}">Business reconciliation: ${esc(phase.model_status)}</span><span class="${phase.quality_status==='FAIL'?'bad':''}">Native quality: ${esc(phase.quality_status)}</span></div>`;
}
function businessQuestion(stage,label){
  const question=session.case[stage];
  return `<form data-business-action="${stage}">${select('choice',esc(question.prompt),question.options.map(([key,text])=>[esc(key),esc(text)]))}${stage==='diagnose'?`<div class="field"><label for="reason">Explain the evidence in your own words (optional)</label><textarea id="reason" name="reason">${esc(draft.reason||'')}</textarea><small class="field-hint">Saved for reflection. Structured choices are graded; prose is not automatically certified.</small></div>`:''}${primary(label,stage)}</form>`;
}
function businessChecks(){
  const labels={complete_business_rows:'Every business field matches the independent expected output',declared_key:'Native key assertions pass',native_quality_gate:'Native quality contract is open',quarantine_accounted:'All rejected records are accounted for',repair_reconciled:'The repaired snapshot reconciles',deterministic_replay:'Repeating the transformation preserves the same output',published_snapshot_matches:'The released snapshot matches validated business rows',fault_evidence_retained:'The original failure evidence is retained'};
  if(!session.verification)return '';
  return `<ul class="checks">${Object.entries(session.verification.checks).map(([key,ok])=>`<li><i class="${ok?'':'bad'}">${ok?'✓':'✕'}</i>${esc(labels[key]||key)}</li>`).join('')}</ul>`;
}
function architectureReason(){
  const c=session.case;
  return `<div class="why-card"><span class="eyebrow">WHY THIS ARCHITECTURE?</span><p>${esc(c.why)}</p><details><summary>Tradeoffs and when the choice changes</summary><p>${esc(c.tradeoff)}</p></details></div>`;
}
function dataTable(rows){
  if(!rows?.length)return '<p class="note">No rows in this set.</p>';
  const columns=Object.keys(rows[0]);
  return `<div class="table-scroll"><table><thead><tr>${columns.map(col=>`<th>${esc(col)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(col=>`<td>${esc(row[col])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function businessEvidence(){
  const entries=Object.keys(session.evidence);
  $('evidence-panel').hidden=!entries.length;
  if(!entries.length)return;
  if(!entries.includes(evidencePhase))evidencePhase=entries.at(-1);
  const phase=session.evidence[evidencePhase];
  $('evidence-panel').innerHTML=`<div class="evidence-top"><div><span class="eyebrow">FOLLOW THE EVIDENCE</span><h2>Inspect the actual business output</h2></div><select id="phase-select" aria-label="Evidence phase">${entries.map(name=>`<option value="${name}" ${name===evidencePhase?'selected':''}>${{baseline:'Healthy reference',fault:'Injected failure',recovery:'Repaired output',rerun:'Repeated transformation'}[name]}</option>`).join('')}</select></div>${businessMetrics(phase)}${dataTable(phase.rows)}${phase.quarantine.length?`<h3>Quarantine · retained for investigation</h3>${dataTable(phase.quarantine)}`:''}<details><summary>Source fixture tables</summary>${Object.entries(session.inputs).map(([name,table])=>`<h3>${esc(name)} · ${esc(table.grain)}</h3>${dataTable(table.rows.map(row=>Object.fromEntries(Object.keys(table.columns).map((col,i)=>[col,row[i]]))))}`).join('')}</details><details><summary>Executed transformation SQL</summary><pre><code>${esc(phase.sql)}</code></pre></details><p class="note">${esc(phase.scope)}</p><p class="note">Native quality checks schema, grain and volume; independent full-row business reconciliation supplies the wider publication decision. A quality PASS alone does not certify business meaning.</p>`;
  $('phase-select').addEventListener('change',event=>{evidencePhase=event.target.value;businessEvidence();});
}
function renderBusiness(){
  const c=session.case,step=session.step;
  $('workspace-topic').textContent=c.sector;
  $('priority-label').textContent='ANALYTICS ENGINEERING · '+c.priority;
  $('scenario-label').innerHTML=String(c.number).padStart(2,'0')+` <span>${esc(c.concept)}</span>`;
  $('architecture-title').textContent='Trace the business decision.';
  $('steps').innerHTML=steps.map((name,i)=>`<div class="step-item ${i<step?'done':i===step?'active':''}" ${i===step?'aria-current="step"':''}><span class="number">${i<step?'✓':String(i+1).padStart(2,'0')}</span><span class="step-name">${name}</span></div>`).join('');
  const latest=session.evidence.rerun||session.evidence.recovery||session.evidence.fault;
  const mode=!latest?'ready':latest.publication==='BLOCKED'?'failed':'recovered';
  $('graph-state').textContent=mode==='ready'?'Ready to explore':mode==='failed'?'Business trust blocked':'Validated output';
  $('pipeline').innerHTML=c.layers.map(([name,label],i)=>`${i?'<span class="arrow" aria-hidden="true">→</span>':''}<button class="node ${i===selectedNode?'selected':''} ${mode==='failed'?(i===c.fault_layer?'failed':i>c.fault_layer?'impact':''):mode==='recovered'?'recovered':''}" data-node="${i}" aria-label="Explore ${esc(name)}"><span class="node-icon" aria-hidden="true">${['▤','⇥','▱','◇','✓','▥'][i]}</span><b>${esc(name)}</b><small>${esc(label)}</small></button>`).join('');
  $('node-detail').innerHTML=`<strong>${esc(c.layers[selectedNode][0])}</strong>${esc(c.layers[selectedNode][2])}`;
  const titles=[c.title,'Predict before you run.','Run the business failure.','Read the evidence.','Locate the architectural cause.','Choose the repair.','Verify the business result.','Recall the design rule.','Defend the architecture.'];
  let html=`<div class="lesson-kicker"><span class="step-chip">${step<9?String(step+1).padStart(2,'0')+' / '+steps[step].toUpperCase():'EXERCISE COMPLETE'}</span><span class="time-tag">ONE BUSINESS PROBLEM</span></div><h2>${esc(step<9?titles[step]:'Business case completed.')}</h2>`;
  if(step===0)html+=`<p>${esc(c.story)}</p><div class="story"><b>Design constraints</b><ul>${c.requirements.map(text=>`<li>${esc(text)}</li>`).join('')}</ul></div>${primary('Begin this business problem')}`;
  if(step===1)html+=`<p>Use the business constraints and the diagram. The actual outcome stays hidden until you run it.</p>${businessQuestion('predict','Save my prediction')}`;
  if(step===2)html+=`<p>The lab will execute a healthy reference and a different, faulty SQL transformation over pinned synthetic fixtures.</p><div class="story">Real local SQL, native key checks, native quality contracts.<br>External source conditions are simulated fixture facts.</div>${primary('Run the failure','run')}`;
  if(step===3)html+=`<p>Compare the output with the business requirement. A successful query and unique keys can still produce an untrustworthy result.</p>${feedback('predict')}${businessMetrics(session.evidence.fault)}<p>Inspect the source and output rows below before diagnosing.</p>${primary('Diagnose this failure')}`;
  if(step===4)html+=`<p>Choose the first incorrect architectural decision, using the evidence below.</p>${feedback('diagnose')}${businessQuestion('diagnose','Check my diagnosis')}`;
  if(step===5)html+=`${architectureReason()}${businessQuestion('fix','Execute this repair')}`;
  if(step===6)html+=`<p>Re-execute the repaired transformation, compare all business fields, and check the released local snapshot. This proves deterministic fixture replay; it does not certify a live distributed connector.</p>${businessMetrics(session.evidence.recovery)}${primary('Verify the repaired result','verify')}`;
  if(step===7)html+=`<p>Apply the design rule to a short follow-up without reopening the explanation.</p>${feedback('recall')}${businessQuestion('recall','Check my recall')}`;
  if(step===8)html+=`${architectureReason()}<div class="story">${esc(c.details)}</div>${businessChecks()}<p>Walk the diagram from the consumer backward: which requirement forces the boundary, and when would you choose a simpler design?</p>${primary('Complete this business case')}`;
  if(step===9)html+=`<p>You predicted, diagnosed, repaired, verified, and recalled this business problem. Guided choices record exercise completion; independent design reasoning needs further practice.</p>${businessChecks()}<div class="button-row"><button class="primary" id="choose-next">Choose another business problem →</button><button class="secondary" id="repeat">Repeat this problem</button></div>`;
  if(step>=5)html+=`<details class="sources"><summary>Learning sources and simulation scope</summary><p>${esc(c.limits)}</p><p>Original scenarios organized around <a href="https://datadriven.io/learn/pa_pattern_design_pipeline_intermediate" target="_blank" rel="noopener">DataDriven's pipeline-design lesson</a>.</p>${c.source_links.length?`<ul>${c.source_links.map(url=>`<li><a href="${esc(url)}" target="_blank" rel="noopener">${esc(new URL(url).hostname)}</a></li>`).join('')}</ul>`:''}</details>`;
  $('lesson').innerHTML=html;
  $('session-info').innerHTML=`<div class="eyebrow">YOUR SESSION</div><strong>${esc(c.id)} · ${esc(session.run_id.slice(0,8))}</strong>Progress saves after each step.<br>${session.assistance.automated_demo?'Automated UI demonstration':'Guided business design practice'}<br><span class="state">${esc(session.state)}</span>`;
  document.querySelectorAll('[data-node]').forEach(button=>button.addEventListener('click',()=>{selectedNode=Number(button.dataset.node);render();}));
  document.querySelectorAll('form[data-business-action]').forEach(form=>form.addEventListener('submit',event=>{event.preventDefault();const answer=Object.fromEntries(new FormData(form));draft=answer;act(form.dataset.businessAction,answer);}));
  document.querySelectorAll('form input,form select,form textarea').forEach(input=>input.addEventListener('input',()=>{draft[input.name]=input.value;}));
  document.querySelectorAll('button[data-action]').forEach(button=>{if(!button.closest('form'))button.addEventListener('click',()=>act(button.dataset.action));});
  $('repeat')?.addEventListener('click',()=>newSession(session.scenario_id));
  $('choose-next')?.addEventListener('click',showCatalog);
  businessEvidence();
}
