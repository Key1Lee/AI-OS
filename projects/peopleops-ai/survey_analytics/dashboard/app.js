(() => {
 'use strict';
 let gold = window.SURVEY_DATA.gold;
 const snapshot = window.SURVEY_DATA.snapshot;
 const $ = id => document.getElementById(id);
 const count = n => Number(n).toLocaleString('en-US');
 const value = n => n === null || n === undefined ? '—' : Number(n).toFixed(1);
 const signed = n => n === null || n === undefined ? '—' : `${n > 0 ? '+' : ''}${value(n)}`;
 const set = (id, text) => { $(id).textContent = text; };
 function selected() { return gold?.department_breakdown.find(s => s.department === $('department').value); }
 function render() {
   if (!gold) { set('notice', 'No Gold snapshot yet. Run the n8n pipeline to collect and visualize 5,000 fictional employee responses.'); return; }
   const segment = selected(); const metrics = segment?.metrics || gold.metrics; const counts = segment?.counts || gold.counts;
   set('participation', `${value(100 * counts.completed / counts.invited)}%`);
   set('participants-note', `${count(counts.completed)} of ${count(counts.invited)} fictional employees`);
   $('experience').innerHTML = `${value(metrics.experience_score.value)} <em>/ 100</em>`;
   set('experience-note', `${count(metrics.experience_score.denominator)} answered · skipped questions excluded`);
   set('csat', `${value(metrics.csat_top_two_box.value)}%`); set('csat-note', `${count(metrics.csat_top_two_box.numerator)} favorable / ${count(metrics.csat_top_two_box.denominator)} answered`);
   set('enps', signed(metrics.enps.value)); set('enps-note', `${count(metrics.enps.denominator)} answered · range −100 to +100`);
   const key = $('metric').value; const negative = key === 'enps';
   set('axis-min', negative ? '−100' : '0'); set('axis-mid', negative ? '0' : '50');
   const rows = (segment ? [segment] : [...gold.department_breakdown]).sort((a,b) => (b.metrics[key].value ?? -Infinity) - (a.metrics[key].value ?? -Infinity));
   $('chart').replaceChildren();
   for (const row of rows) {
     const metric = row.metrics[key]; const bar = document.createElement('div'); bar.className = 'bar-row';
     const label = document.createElement('div'); label.className = 'bar-name'; label.textContent = row.department;
     const sample = document.createElement('small'); sample.textContent = `n = ${count(metric.denominator)} answered`; label.append(sample);
     const track = document.createElement('div'); track.className = 'bar-track';
     if (negative) { const zero = document.createElement('i'); zero.className = 'zero-line'; track.append(zero); }
     const fill = document.createElement('div'); fill.className = 'bar-fill';
     if (negative) { fill.style.left = `${metric.value < 0 ? 50 + metric.value/2 : 50}%`; fill.style.width = `${Math.abs(metric.value)/2}%`; if(metric.value < 0) fill.style.background = '#be876f'; }
     else { fill.style.left = '0'; fill.style.width = `${metric.value ?? 0}%`; }
     track.append(fill); const number = document.createElement('span'); number.className = 'bar-value'; number.textContent = negative ? signed(metric.value) : value(metric.value);
     bar.append(label, track, number); $('chart').append(bar);
   }
   $('chart').setAttribute('aria-label', `${$('metric').selectedOptions[0].text}: ${rows.map(r=>`${r.department} ${r.metrics[key].value}, ${r.metrics[key].denominator} answers`).join('; ')}`);
   $('detail').replaceChildren();
   for (const row of rows) {
     const tr = document.createElement('tr'); const name = document.createElement('td'); name.textContent = row.department; tr.append(name);
     const responses = document.createElement('td'); responses.textContent = count(row.counts.completed); tr.append(responses);
     for (const metricKey of ['experience_score','csat_top_two_box','enps']) { const m = row.metrics[metricKey]; const td = document.createElement('td'); const score = document.createElement('span'); score.textContent = metricKey === 'enps' ? signed(m.value) : `${value(m.value)}${metricKey==='csat_top_two_box'?'%':''}`; if(metricKey==='experience_score') score.className='score-pill'; const small = document.createElement('small'); small.textContent = `${count(m.denominator)} answered`; td.append(score, small); tr.append(td); }
     $('detail').append(tr);
   }
   set('department-count', `${rows.length} department${rows.length===1?'':'s'} shown`);
   set('bronze-note', `${count(gold.quality.unique_versions)} unique response versions preserved`);
   set('silver-note', `${count(gold.quality.accepted_responses)} accepted · ${gold.quality.quarantined_responses} quarantined`);
   set('gold-note', `${gold.department_breakdown.length} department aggregates · ${gold.metric_version}`);
   set('batch', gold.batch_id.slice(0,24)+'…'); $('batch').title = gold.batch_id;
   set('published', gold.published_at ? `Gold published ${new Date(gold.published_at).toLocaleString()}` : 'Persisted Gold snapshot');
   for(const ext of ['csv','html']) { $(ext).href = snapshot ? `http://127.0.0.1:8812/analytics/export/${gold.batch_id}/${ext}` : `/analytics/export/${gold.batch_id}/${ext}`; $(ext).setAttribute('aria-disabled','false'); }
 }
 function populate() { const previous=$('department').value; $('department').replaceChildren(new Option('All departments','all')); if(gold) for(const row of gold.department_breakdown) $('department').add(new Option(row.department,row.department)); $('department').value = [...$('department').options].some(o=>o.value===previous)?previous:'all'; }
 $('department').addEventListener('change', render); $('metric').addEventListener('change', render);
 $('run').addEventListener('click', async () => { $('run').disabled=true; set('run','Collecting → validating → publishing…'); $('notice').classList.remove('error'); set('notice','n8n is collecting all 5,000 synthetic responses and rebuilding the Gold visualization.'); try { const response=await fetch('/analytics/run',{method:'POST'}); if(!response.ok) throw new Error('The local n8n run did not complete. Check the error inbox and workflow execution.'); const data=await fetch('/analytics'); if(!data.ok) throw new Error('Gold data is unavailable.'); gold=await data.json(); populate(); render(); set('notice','Pipeline completed. All 5,000 fictional employee responses are included; scores use answered questions only.'); } catch(error) { $('notice').classList.add('error'); set('notice',error.message); } finally { $('run').disabled=false; set('run','↻ Run n8n pipeline'); } });
 if(snapshot) { $('run').disabled=true; set('run','Saved Gold snapshot'); }
 populate(); render();
})();
