import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';

const root=path.resolve(import.meta.dirname,'..');
const workflow=JSON.parse(await readFile(path.join(root,'workflows','northstar-leadops.json'),'utf8'));
const byName=name=>workflow.nodes.find(n=>n.name===name);
const run=(source,$json,$node={})=>new Function('$json','$node',source)($json,$node);
const normalize=byName('Validate & Normalize [D]').parameters.jsCode;
const qualify=byName('Validate AI + Score & Route [D]').parameters.jsCode;
const files=(await readdir(path.join(root,'fixtures'))).filter(x=>x.endsWith('.json')).sort();
const fixtures=await Promise.all(files.map(async x=>JSON.parse(await readFile(path.join(root,'fixtures',x),'utf8'))));
const failures=[];
const assert=(condition,message)=>{if(!condition)failures.push(message)};

for(const f of fixtures){
  const normalized=run(normalize,f.input)[0].json;
  if(f.expected.http===422){
    assert(!normalized.valid,`${f.name}: expected validation rejection`);
    continue;
  }
  assert(normalized.valid,`${f.name}: expected valid normalized payload`);
  assert(normalized.email===String(f.input.lead.email).trim().toLowerCase(),`${f.name}: email normalization`);
  assert(normalized.source===String(f.input.source).trim().toLowerCase(),`${f.name}: source normalization`);
  if(f.mocks.ai){
    const base={...normalized,hubspot_contact_id:null,crm_action:'create',enrichment_status:'skipped_optional'};
    const result=run(qualify,{output:f.mocks.ai},{'Build Qualification Context':{json:base}})[0].json;
    assert(result.fit_tier===f.expected.tier,`${f.name}: expected ${f.expected.tier}, got ${result.fit_tier}`);
    assert(result.human_review_required===f.expected.human_review,`${f.name}: human-review mismatch`);
  }
}

const timeout=fixtures.find(f=>f.name==='12_llm_timeout');
const timeoutBase=run(normalize,timeout.input)[0].json;
const timeoutResult=run(qualify,{error:{message:'timeout'}},{'Build Qualification Context':{json:timeoutBase}})[0].json;
assert(timeoutResult.fit_tier==='MANUAL_REVIEW','LLM timeout must route to MANUAL_REVIEW');

const extra={intent:'automation_project',pain_points:[],budget_band:'unknown',urgency_band:'unknown',recommended_next_action:'sales_call',confidence:.9,summary:'ok',unexpected:'reject me'};
const hotBase=run(normalize,fixtures[0].input)[0].json;
const extraResult=run(qualify,{output:extra},{'Build Qualification Context':{json:hotBase}})[0].json;
assert(extraResult.fit_tier==='MANUAL_REVIEW'&&!extraResult.ai_schema_valid,'additional AI properties must be rejected');

if(failures.length){console.error('FAIL\n- '+failures.join('\n- '));process.exit(1)}
console.log(`PASS: ${fixtures.length} normalization cases; structured scoring/routing cases; malformed, extra-property, timeout, budget-conflict, and prompt-injection gates.`);
