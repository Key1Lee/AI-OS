import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const load=async p=>JSON.parse(await readFile(p,'utf8'));
const main=await load(path.join(root,'workflows','northstar-leadops.json'));
const error=await load(path.join(root,'workflows','northstar-error-handler.json'));
const sql=await readFile(path.join(root,'db','001_schema.sql'),'utf8');
const fixtureFiles=(await readdir(path.join(root,'fixtures'))).filter(x=>x.endsWith('.json')).sort();
const fixtures=await Promise.all(fixtureFiles.map(x=>load(path.join(root,'fixtures',x))));
const failures=[];
const ok=(v,m)=>{if(!v)failures.push(m)};

for(const w of [main,error]){
  ok(w.name&&Array.isArray(w.nodes)&&w.nodes.length>0,`${w.name||'workflow'} structure`);
  const names=new Set(w.nodes.map(n=>n.name));
  for(const [from,outputs] of Object.entries(w.connections||{})){
    ok(names.has(from),`missing source node ${from}`);
    for(const group of Object.values(outputs)) for(const branch of group) for(const c of branch) ok(names.has(c.node),`missing target node ${c.node}`);
  }
}
ok(main.settings.errorWorkflow===error.id,'main errorWorkflow id mismatch');
const mainText=JSON.stringify(main);
ok(/ON CONFLICT \(idempotency_key\) DO UPDATE[\s\S]*locked_at < NOW\(\)-INTERVAL '30 minutes'[\s\S]*RETURNING/i.test(mainText),'atomic claim/reclaim missing');
ok(/queryReplacement/.test(JSON.stringify(main)),'parameterized SQL configuration missing');
ok(/additionalProperties/.test(JSON.stringify(main))&&/ai_outputParser/.test(JSON.stringify(main)),'strict AI schema missing');
ok(!/sk-[A-Za-z0-9]{10,}|xox[baprs]-|pat-[A-Za-z0-9]/.test(JSON.stringify([main,error])),'possible committed secret');
ok(sql.includes('PRIMARY KEY')&&sql.includes('workflow_errors')&&sql.includes('CHECK (status IN'),'SQL constraints missing');
ok(sql.includes('workflow_effects')&&sql.includes('notification_status'),'side-effect ledger schema missing');
ok(!/UNIQUE\s*\(source,\s*event_id\)/i.test(sql),'redundant event uniqueness can race with canonical idempotency key');
const createNode=main.nodes.find(n=>n.name==='HubSpot - Create Contact Once');
ok(createNode&&!createNode.retryOnFail&&createNode.onError==='continueErrorOutput','HubSpot create must not blind-retry');
ok(main.nodes.some(n=>n.name==='HubSpot - Verify Ambiguous Create'),'ambiguous create verification missing');
ok(main.nodes.some(n=>n.name==='Postgres - Mark CRM Failure'),'CRM failure state transition missing');
ok(main.nodes.some(n=>n.name==='Postgres - Claim Notification Effect'),'notification effect claim missing');
ok(main.nodes.some(n=>n.name==='Postgres - Mark Notification Unknown'),'unknown Slack outcome handling missing');
const errorStore=error.nodes.find(n=>n.name==='Postgres - Store Workflow Error');
ok(errorStore?.onError==='continueErrorOutput'&&(error.connections[errorStore.name]?.main?.length===2),'error alert must survive audit DB failure');
ok(fixtureFiles.length===15,`expected 15 fixtures, found ${fixtureFiles.length}`);
for(const f of fixtures){
  ok(f.input&&f.expected,`${f.name} missing input/expected`);
  for(const k of ['http','crm','tier','slack','human_review','db']) ok(Object.hasOwn(f.expected,k),`${f.name} missing expected.${k}`);
}
const scoreFixture=f=>{
  const l=f.input.lead||{}, a=f.mocks.ai||{}; let score=0;
  if(l.employee_count>=50&&l.employee_count<=500)score+=25;
  if(['vp','vice president','chief','director','head','founder','owner'].some(t=>String(l.job_title||'').toLowerCase().includes(t)))score+=20;
  if(['25k_50k','50k_plus'].includes(a.budget_band))score+=20;
  if(['0_7_days','8_30_days'].includes(a.urgency_band))score+=15;
  if(a.intent==='automation_project')score+=15;
  const domain=String(l.email||'').split('@')[1]?.toLowerCase();
  if(domain&&!['gmail.com','yahoo.com','hotmail.com','outlook.com','icloud.com'].includes(domain))score+=5;
  let tier=score>=75?'HOT':score>=50?'WARM':'COLD';
  const schema=typeof a.confidence==='number'&&typeof a.summary==='string'&&Array.isArray(a.pain_points);
  const amount=String(l.message||'').match(/(?:\$|usd\s*)(\d+(?:\.\d+)?)\s*(k|000)?/i);
  let explicit='unknown';if(amount){let n=Number(amount[1]);if((amount[2]||'').toLowerCase()==='k')n*=1000;explicit=n<10000?'under_10k':n<25000?'10k_25k':n<50000?'25k_50k':'50k_plus'}
  const injection=/\b(ignore (all |the )?(previous|prior) instructions|system prompt|developer message|reveal (your )?(secrets|credentials)|delete (all )?(crm|contacts|records)|bypass (security|policy))\b/i.test(String(l.message||''));
  if(!schema||a.confidence<.75||(explicit!=='unknown'&&a.budget_band!=='unknown'&&explicit!==a.budget_band)||injection)tier='MANUAL_REVIEW';
  return tier;
};
for(const f of fixtures.filter(f=>f.mocks.ai)) ok(scoreFixture(f)===f.expected.tier,`${f.name} expected tier ${f.expected.tier}, calculated ${scoreFixture(f)}`);
const required=['01_hot_lead','02_warm_lead','03_cold_student','04_duplicate_same_event','05_existing_contact_new_event','06_missing_email','07_malformed_payload','08_prompt_injection','09_low_ai_confidence','10_crm_429','11_enrichment_500','12_llm_timeout','13_malformed_llm_output','14_budget_conflict','15_expired_crm_credentials'];
for(const n of required) ok(fixtureFiles.includes(n+'.json'),`missing ${n}.json`);

if(failures.length){console.error('FAIL\n- '+failures.join('\n- '));process.exit(1)}
console.log(`PASS: ${main.nodes.length} main nodes; ${error.nodes.length} error nodes; ${fixtures.length} fixtures; atomic claim, strict AI schema, parameterized SQL, error wiring, and secret scan verified.`);
