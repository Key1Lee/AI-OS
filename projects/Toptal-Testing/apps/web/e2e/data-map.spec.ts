import {test,expect} from '@playwright/test';
import path from 'node:path';

test.beforeEach(async({request})=>{
 const config=await (await request.get('/api/config')).json();
 const current=await (await request.get('/api/map/investigations/current')).json();
 if(current)expect((await request.post('/api/map/investigations/'+current.id+'/end',{headers:{'x-trainer-token':config.request_token},data:{learn:false}})).ok()).toBe(true);
});

test('standalone overview, independent assessment, reload and explicit learning transition',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/map');
 await expect(page.getByRole('heading',{name:'Data System Map',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:/^Expand /})).toHaveCount(5);
 await expect(page.getByRole('button',{name:/^Open node /})).toHaveCount(0);
 await page.screenshot({path:path.resolve('../../docs/screenshots/map-overview.png'),fullPage:true});
 await page.getByRole('button',{name:'Start Assessment',exact:true}).click();
 await expect(page.getByText('First assessment without recorded prior exposure.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Show failure path',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Follow the observed failure'})).toBeVisible();
 await expect(page.locator('.dm-learning-evidence')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Explain this system',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Open node fct_orders',exact:true}).click();
 await page.getByRole('tab',{name:'Recorded tests',exact:true}).click();
 await expect(page.getByText('Failure count: 2',{exact:false})).toBeVisible();
 await page.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('Retained across reload; observed duplicate order IDs.');
 await page.getByRole('textbox',{name:'Working hypothesis',exact:true}).fill('Inspect parent grain before asserting causality.');
 await page.getByRole('button',{name:'Save diagnosis draft'}).click();
 await expect(page.getByRole('status')).toContainText('Saved to this profile');
 const session=await (await page.request.get('/api/map/investigations/current')).json();
 await page.reload();
 await expect(page.getByRole('textbox',{name:'Evidence notes',exact:true})).toHaveValue('Retained across reload; observed duplicate order IDs.');
 await expect(page.getByRole('textbox',{name:'Working hypothesis',exact:true})).toHaveValue('Inspect parent grain before asserting causality.');
 await expect(page.locator('.dm-learning-evidence')).toHaveCount(0);
 await page.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('An unsaved edit is retained when ending assessment.');
 await page.getByRole('button',{name:'End assessment and learn'}).click();
 await expect(page.getByRole('button',{name:'Finish learning'})).toBeVisible();
 const ended=await (await page.request.get('/api/map/investigations/'+session.id)).json();
 expect(ended.status).toBe('abandoned');expect(ended.draft.notes).toBe('An unsaved edit is retained when ending assessment.');
 await page.getByRole('button',{name:'Show failure path',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Earliest observed anomaly: int order items'})).toBeVisible();
 await expect(page.getByText('First bad node cannot yet be established.',{exact:true})).toBeVisible();
 await expect(page.locator('.dm-learning-evidence')).toContainText('stg orders');
 await page.screenshot({path:path.resolve('../../docs/screenshots/map-learning-incident.png'),fullPage:true});
 expect(errors).toEqual([]);
});

test('trainer map investigation scores observed actions and persists result without SQL execution',async({page})=>{
 await page.goto('/#data-map');
 await page.getByRole('button',{name:'Start Learning',exact:true}).click();
 await page.getByRole('button',{name:'Show failure path',exact:true}).click();
 await page.getByRole('button',{name:'Open node fct_orders',exact:true}).click();
 for(const tab of ['Schema','Recorded tests','Upstream','Impact']){
  await page.getByRole('tab',{name:tab,exact:true}).click();
  await expect(page.getByRole('tab',{name:tab,exact:true})).toBeEnabled();
 }
 await page.getByRole('button',{name:'Open node int_order_items',exact:true}).click();
 await page.getByRole('tab',{name:'SQL',exact:true}).click();
 await expect(page.locator('.dm-code')).toContainText('LEFT JOIN');
 await page.getByRole('textbox',{name:'Working hypothesis',exact:true}).fill('The item join may duplicate orders; check order uniqueness.');
 await page.getByRole('button',{name:'Record hypothesis'}).click();
 await expect(page.getByRole('textbox',{name:'Working hypothesis',exact:true})).toBeEmpty();
 await page.getByRole('combobox',{name:'Observed failure',exact:true}).selectOption('model.commerce.fct_orders');
 await page.getByRole('combobox',{name:'Suspected origin',exact:true}).selectOption('model.commerce.int_order_items');
 await page.getByRole('combobox',{name:'Expected fact grain',exact:true}).selectOption('one_row_per_order');
 await page.getByLabel('Daily Revenue',{exact:true}).check();
 await page.getByLabel('Executive Dashboard',{exact:true}).check();
 await page.getByRole('textbox',{name:'Proposed fix',exact:true}).fill('Aggregate items to order grain before joining.');
 await page.getByRole('textbox',{name:'Verification plan',exact:true}).fill('Rebuild and compare uniqueness plus revenue total.');
 await page.getByRole('button',{name:'Submit investigation',exact:true}).click();
 await expect(page.locator('.dm-score strong')).toHaveText('8 / 8');
 await expect(page.getByText('Learning or repeated exposure: this session cannot earn independent credit.')).toBeVisible();
 const records=await (await page.request.get('/api/map/investigations/history')).json();
 expect(records[0].result.independent).toBe(false);
 const complete=await (await page.request.get('/api/map/investigations/'+records[0].id)).json();
 expect(complete.telemetry.tests_executed).toBe(0);expect(complete.telemetry.verification_performed).toBe(false);
 expect(complete.actions.some((a:any)=>a.kind==='hypothesis')).toBe(true);
 await page.reload();await expect(page.locator('.dm-score strong')).toHaveText('8 / 8');
 await page.getByText('Saved diagnosis',{exact:true}).click();
 await expect(page.getByText('Aggregate items to order grain before joining.',{exact:true})).toBeVisible();
 await expect(page.getByText('Rebuild and compare uniqueness plus revenue total.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Submit investigation',exact:true})).toHaveCount(0);
});

test('local artifact import keeps unknown metadata and renders uploaded SQL as inert text',async({page})=>{
 await page.goto('/map');
 await page.getByText('Import dbt artifact files',{exact:true}).click();
 await page.getByLabel('System ID',{exact:true}).fill('browser-import');
 await page.getByLabel('System name',{exact:true}).fill('Browser imported system');
 const manifest={nodes:{'model.demo.unmapped_model':{name:'unmapped_model',resource_type:'model',raw_code:'SELECT \'<script>window.injected=true</script>\''}}};
 await page.getByLabel('manifest.json (required)',{exact:true}).setInputFiles({name:'manifest.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(manifest))});
 await page.getByRole('button',{name:'Import metadata',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Browser imported system',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Start Assessment',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Expand Unclassified',exact:true}).click();
 await page.getByRole('button',{name:'Open node unmapped_model',exact:true}).click();
 await expect(page.getByText('Grain unknown',{exact:true})).toBeVisible();
 await expect(page.getByText('Primary key unknown',{exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'Schema',exact:true}).click();
 await expect(page.getByText('Schema unknown. Import catalog metadata if available.')).toBeVisible();
 await page.getByRole('tab',{name:'SQL',exact:true}).click();
 await expect(page.locator('.dm-code')).toContainText('<script>window.injected=true</script>');
 expect(await page.evaluate(()=>(window as any).injected)).toBeUndefined();
});

test('narrow light view scrolls the graph locally and stage expansion is keyboard usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/map');
 await page.getByRole('button',{name:'Change appearance',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 const stage=page.getByRole('button',{name:'Expand Sources',exact:true});await stage.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('button',{name:'Open node raw_orders',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
 await page.screenshot({path:path.resolve('../../docs/screenshots/map-mobile-light.png'),fullPage:true});
});

test('a stale map tab preserves both drafts and requires explicit browser-note restoration',async({page,context})=>{
 await page.goto('/map');await page.getByRole('button',{name:'Start Learning',exact:true}).click();
 await expect(page.getByRole('textbox',{name:'Evidence notes',exact:true})).toBeVisible();
 const current=await (await page.request.get('/api/map/investigations/current')).json();
 const second=await context.newPage();await second.goto('/map');
 await expect(second.getByRole('textbox',{name:'Evidence notes',exact:true})).toBeVisible();
 await page.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('First tab saved evidence.');
 await page.getByRole('button',{name:'Save diagnosis draft'}).click();
 await expect(page.getByRole('status')).toContainText('Saved to this profile');
 await second.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('Second tab unsynced evidence.');
 await second.getByRole('button',{name:'Save diagnosis draft'}).click();
 await expect(second.getByRole('alert')).toContainText('draft changed or ended');
 expect((await (await page.request.get('/api/map/investigations/'+current.id)).json()).draft.notes).toBe('First tab saved evidence.');
 await second.reload();
 await expect(second.getByRole('textbox',{name:'Evidence notes',exact:true})).toHaveValue('First tab saved evidence.');
 await expect(second.getByRole('button',{name:'Restore browser notes'})).toBeVisible();
 await second.getByRole('button',{name:'Restore browser notes'}).click();
 await expect(second.getByRole('textbox',{name:'Evidence notes',exact:true})).toHaveValue('Second tab unsynced evidence.');
 expect((await (await page.request.get('/api/map/investigations/'+current.id)).json()).draft.notes).toBe('First tab saved evidence.');
 await second.close();
});

test('a first tab save cannot erase another tab earlier unsaved notes',async({page,context})=>{
 await page.goto('/map');await page.getByRole('button',{name:'Start Learning',exact:true}).click();
 await expect(page.getByRole('textbox',{name:'Evidence notes',exact:true})).toBeVisible();
 const second=await context.newPage();await second.goto('/map');
 await second.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('Earlier second-tab unsaved notes.');
 await page.getByRole('textbox',{name:'Evidence notes',exact:true}).fill('Later first-tab saved notes.');
 await page.getByRole('button',{name:'Save diagnosis draft'}).click();
 await expect(page.getByRole('status')).toContainText('Saved to this profile');
 await second.reload();
 await expect(second.getByRole('textbox',{name:'Evidence notes',exact:true})).toHaveValue('Later first-tab saved notes.');
 await expect(second.getByRole('button',{name:'Restore browser notes'})).toBeVisible();
 await second.getByRole('button',{name:'Restore browser notes'}).click();
 await expect(second.getByRole('textbox',{name:'Evidence notes',exact:true})).toHaveValue('Earlier second-tab unsaved notes.');
 await second.close();
});
