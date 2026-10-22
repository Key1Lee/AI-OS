import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
async function main() {
 const p=JSON.parse(readFileSync(0,'utf8'));
 const {simulate,planBackfill,simulateBackfill}=await import(pathToFileURL(resolve(p.project,'src/engine/index.ts')).href);
 const definitions=[['ingest','ingest',[],'raw'],['resolve','transform',['ingest'],'silver'],['publish','mart',['resolve'],'gold']];
 const tasks=definitions.map(([id,stage,dependencies,output])=>({id,name:id,purpose:'Declared SQL lab replay schedule; no real job execution',stage,dependencies,trigger:'workflow',trigger_rule:'all_success',duration_minutes:1,timeout_minutes:5,retry_policy:{max_attempts:2,delay_minutes:1,retryable_errors:['transient']},inputs:id==='ingest'?['source']:[id==='resolve'?'raw':'silver'],outputs:[output],idempotent:true,outcomes:id==='ingest'?[{type:'transient',message:'Authored partial-ingestion failure'},'success']:['success'],enabled:true,resource_pool:'warehouse',write_mode:'replace',output_rows:p.rows}));
 const workflow={id:'sql_lab_replay',name:'SQL Lab replay',purpose:'Native dependency/retry/backfill simulation',tasks,assets:[{id:'source',name:'Source',producer_task_id:null},...tasks.map(t=>({id:t.outputs[0],name:t.outputs[0],producer_task_id:t.id}))],schedule:{frequency:'daily',time:'06:00',timezone:'Asia/Seoul'},asset_triggers:['source'],pools:{warehouse:1},expected_ready_time:'07:00'};
 const run=simulate(workflow,{run_id:p.run_id,partition:'2026-10-02',clock_date:'2026-10-03',start_minute:360,trigger:{kind:'manual'},max_concurrency:1});
 const plan=planBackfill('2026-10-01','2026-10-02','2026-10-03',[],'replace');
 const backfill=simulateBackfill(workflow,plan,{execution_id:p.run_id,workers:1,partition_concurrency:1});
 process.stdout.write(JSON.stringify({run,backfill,provenance:'Native orchestration simulate / planBackfill / simulateBackfill. Virtual schedule only; PostgreSQL results measured separately.'}));
}
main().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
