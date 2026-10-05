import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
mkdirSync('../docs/screenshots',{recursive:true});

async function open(page:Page){await page.goto('/');await expect(page.getByRole('heading',{name:/Can we trust it/})).toBeVisible();}
async function run(page:Page){await page.getByRole('button',{name:'Run validation',exact:true}).click();await expect(page.getByRole('button',{name:'Run validation',exact:true})).toBeEnabled();}

test('valid, duplicate, evidence, repair and export journey',async({page})=>{
  await open(page);
  await expect(page.getByText('The gate is waiting for evidence')).toBeVisible();
  await expect(page.getByRole('button',{name:'Export evidence'})).toBeDisabled();
  await run(page);
  await expect(page.getByText('Quality gate open',{exact:true})).toBeVisible();
  await expect(page.getByText('10 rows / 10 IDs',{exact:true})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/valid-desktop.png',fullPage:true});
  await page.getByRole('button',{name:/Duplicate order 1007/}).click();
  await expect(page.getByText('The gate is waiting for evidence')).toBeVisible();
  await expect(page.getByRole('button',{name:'Export evidence'})).toBeDisabled();
  await page.getByLabel('Predict the selected check').selectOption('FAIL');
  await run(page);
  await expect(page.getByText('Quality gate blocked',{exact:true})).toBeVisible();
  await expect(page.getByText('11 rows / 10 IDs',{exact:true})).toBeVisible();
  await expect(page.locator('tr.affected')).toHaveCount(2);
  await expect(page.getByText(/You predicted/)).toContainText('FAIL');
  await page.screenshot({path:'../docs/screenshots/duplicate-desktop.png',fullPage:true});
  const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Export evidence'}).click();
  expect((await downloaded).suggestedFilename()).toBe('quality-evidence.json');
  await page.getByRole('button',{name:'Fix fixture & verify again'}).click();
  await expect(page.getByText('The gate is waiting for evidence')).toBeVisible();
  await run(page);await expect(page.getByText('Quality gate open',{exact:true})).toBeVisible();
});

test('mandatory orphan, schema, stale and unpaid failures',async({page})=>{
  await open(page);
  for(const [button,rule] of [['Use missing customer C999','customer_id has a parent'],['Remove ordered_at','Schema matches the contract'],['Advance the clock 3 hours','Data arrived within 2 hours'],['Complete an unpaid order','Completed orders are paid']]){
    await page.getByRole('button',{name:'Reset lab'}).click();
    await page.getByRole('button',{name:new RegExp(button)}).click();
    await expect(page.getByRole('button',{name:'Run validation',exact:true})).toBeEnabled();
    await page.getByRole('button',{name:rule,exact:true}).click();
    await run(page);await expect(page.getByText('Quality gate blocked',{exact:true})).toBeVisible();
    await expect(page.locator('.evidence-panel .badge')).toContainText('FAIL');
    if(button==='Remove ordered_at'){await expect(page.locator('.missing').first()).toHaveText('COLUMN MISSING');}
    if(button==='Advance the clock 3 hours'){await expect(page.locator('.clock')).toContainText('12:00');await expect(page.locator('.fact-evidence')).toContainText('210');}
  }
});

test('warning continues; empty table stays unknown and blocked',async({page})=>{
  await open(page);await page.getByRole('button',{name:/Remove optional descriptions/}).click();await run(page);
  await expect(page.getByText('Quality gate open',{exact:true})).toBeVisible();
  await expect(page.getByText('Nonblocking warnings remain. All blocking checks pass.')).toBeVisible();
  await page.getByRole('button',{name:'Descriptions are at least 90% complete',exact:true}).click();
  await expect(page.locator('.evidence-panel .badge')).toContainText('WARN');
  await page.getByRole('button',{name:'Reset lab'}).click();await page.getByRole('button',{name:/Lose every order/}).click();await run(page);
  await expect(page.getByText('Quality gate blocked',{exact:true})).toBeVisible();
  await expect(page.locator('.evidence-panel .badge')).toContainText('UNKNOWN');
});

test('contract, builder, compiled rule and blocking policy',async({page})=>{
  await open(page);await page.getByRole('button',{name:'Data contract',exact:true}).click();
  await expect(page.getByText('One current record for each order.',{exact:false})).toBeVisible();
  await expect(page.getByText('Commerce Analytics',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Rule builder',exact:true}).click();
  await page.getByLabel('Column',{exact:true}).selectOption('customer_id');
  await page.getByLabel('Severity',{exact:true}).selectOption('WARNING');
  await page.getByRole('button',{name:'Add rule & return to the lab'}).click();await run(page);
  await expect(page.getByText('Quality gate blocked',{exact:true})).toBeVisible();
  await expect(page.locator('.evidence-panel .badge')).toContainText('WARN');
  await expect(page.locator('.policy-line')).toContainText('Blocks publication');
  await page.getByRole('button',{name:'Rule builder',exact:true}).click();await page.getByRole('button',{name:'Remove',exact:true}).click();
  await page.getByRole('button',{name:'Quality gates',exact:true}).click();await run(page);
  await expect(page.getByText('Quality gate open',{exact:true})).toBeVisible();
});

test('compatibility is policy-based and null tightening needs evidence',async({page})=>{
  await open(page);await page.getByRole('button',{name:'Contract evolution',exact:true}).click();
  await page.getByRole('button',{name:'Check compatibility'}).click();await expect(page.getByRole('heading',{name:'Breaking change',exact:true})).toBeVisible();
  await page.getByLabel('Proposed change',{exact:true}).selectOption('optional');
  await page.getByRole('button',{name:'Check compatibility'}).click();await expect(page.getByRole('heading',{name:'Compatible under this policy'})).toBeVisible();
  await page.getByLabel('Consumer forbids optional additions').check();await page.getByRole('button',{name:'Check compatibility'}).click();await expect(page.getByRole('heading',{name:'Breaking change',exact:true})).toBeVisible();
  await page.getByLabel('Proposed change',{exact:true}).selectOption('nullable');await page.getByRole('button',{name:'Check compatibility'}).click();await expect(page.getByRole('heading',{name:'Breaking change',exact:true})).toBeVisible();
  await page.getByLabel('Supply baseline data as null-tightening evidence').check();await page.getByRole('button',{name:'Check compatibility'}).click();await expect(page.getByRole('heading',{name:'Compatible under this policy'})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/compatibility.png',fullPage:true});
});

test('separate unit illustration, seven learning stages and family interfaces',async({page})=>{
  await open(page);
  for(let i=1;i<7;i++)await page.getByRole('button',{name:'Explore next concept'}).click();
  await expect(page.getByText('LEARNING PATH · 7 / 7',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Unit vs data tests',exact:true}).click();
  await page.getByLabel('Break example logic: include cancelled orders').check();
  await expect(page.getByText('Revenue = 300',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'System family',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Is the data valid and safe to use?'})).toBeVisible();
  await page.getByRole('button',{name:'Show dbt adapter output'}).click();await expect(page.locator('pre').last()).toContainText('data_tests:');
  await expect(page.getByText(/Live sibling adapters are future/)).toBeVisible();
});

test('mobile layouts keep content within viewport and support repair',async({page})=>{
  await page.setViewportSize({width:390,height:844});await open(page);await run(page);
  await page.getByRole('button',{name:/Duplicate order 1007/}).click();await run(page);
  await expect(page.getByText('Quality gate blocked',{exact:true})).toBeVisible();
  await page.screenshot({path:'../docs/screenshots/duplicate-mobile.png',fullPage:true});
  for(const view of ['Data contract','Rule builder','Contract evolution','Unit vs data tests','System family','Quality gates']){
    await page.getByRole('button',{name:view,exact:true}).click();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  }
  await page.getByRole('button',{name:'Fix fixture & verify again'}).click();await run(page);await expect(page.getByText('Quality gate open',{exact:true})).toBeVisible();
});

test('all assets and runtime calls stay local with no browser exceptions',async({page})=>{
  const errors:string[]=[];const remote:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(!request.url().startsWith('http://127.0.0.1:8083')&&!request.url().startsWith('blob:'))remote.push(request.url());});
  await open(page);await run(page);await page.getByRole('button',{name:/Change warehouse revenue by/}).click();await run(page);
  await page.getByRole('button',{name:'Net revenue reconciles',exact:true}).click();await expect(page.locator('.fact-evidence')).toContainText('difference 1.00');
  expect(errors).toEqual([]);expect(remote).toEqual([]);
});
