import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

async function writeSQL(page:any,sql:string){
 const input=page.getByRole('textbox',{name:'SQL query editor',exact:true});
 await input.focus();await page.keyboard.press('ControlOrMeta+A');await page.keyboard.insertText(sql);
}

test('dashboard → adaptive SQL → Run → hidden Submit → persisted evidence → next exercise',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Make your next session count.'})).toBeVisible();
 await page.screenshot({path:path.resolve('../../docs/screenshots/dashboard.png'),fullPage:true});
 await page.getByRole('button',{name:'Continue Training',exact:false}).click();
 await expect(page.locator('.monaco-editor')).toBeVisible();
 const id=page.url().split('attempt/')[1];
 const attempt=await (await page.request.get('/api/attempts/'+id)).json();
 const exercise=JSON.parse(fs.readFileSync(path.resolve('../../exercise_bank/sql/'+attempt.exercise.id+'.json'),'utf8'));
 await writeSQL(page,exercise.reference_solution);
 await page.getByRole('button',{name:'▷ Run',exact:true}).click();
 await expect(page.getByText('Query executed',{exact:true})).toBeVisible();
 await page.screenshot({path:path.resolve('../../docs/screenshots/solving.png'),fullPage:true});
 await page.getByRole('button',{name:'Submit →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Correct',exact:true})).toBeVisible();
 await expect(page.getByText('Independent deterministic success',{exact:true})).toBeVisible();
 await expect(page.getByText('4 / 4 categories',{exact:true})).toBeVisible();
 const before=await (await page.request.get('/api/dashboard')).json();
 expect(before.stats.attempts).toBe(1);expect(before.stats.tested).toBeGreaterThan(0);
 expect(before.recommendation.exercise_id).not.toBe(attempt.exercise.id);
 await page.reload();
 await page.getByRole('tab',{name:'Submission review'}).click();
 await expect(page.getByRole('heading',{name:'Correct',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Continue Training ↗',exact:true}).click();
 await expect(page.locator('.solve-heading h1')).not.toHaveText(attempt.exercise.title);
 expect(errors).toEqual([]);
});

test('autosave survives reload and incorrect SQL receives hidden feedback',async({page})=>{
 await page.goto('/#library');
 const card=page.locator('.exercise-card').filter({has:page.getByRole('heading',{name:'Find accounts missing a settled invoice',exact:true})});
 await card.getByRole('button',{name:'Open challenge ↗'}).click();
 await writeSQL(page,"SELECT account_id FROM billing_accounts WHERE account_id NOT IN (SELECT account_id FROM invoices WHERE status='settled' AND period=DATE '2026-09-01')");
 await expect(page.locator('.attempt-status')).toContainText('Saved');
 const id=page.url().split('attempt/')[1];
 await expect.poll(async()=>{const a=await (await page.request.get('/api/attempts/'+id)).json();return a.code;}).toContain('NOT IN');
 await page.reload();await expect(page.locator('.monaco-editor')).toBeVisible();
 await page.getByRole('button',{name:'Submit →',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Partial',exact:true})).toBeVisible();
 await expect(page.getByText('NULL child keys',{exact:true})).toBeVisible();
 await expect(page.getByText('Primary issue to investigate',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Revise this attempt'}).click();
 await expect(page).not.toHaveURL(new RegExp('attempt/'+id));
 await expect(page.locator('.solve-heading h1')).toHaveText('Find accounts missing a settled invoice');
 const revised=page.url().split('attempt/')[1];expect(revised).not.toBe(id);
});

test('strict interview clarifications work and hints are audited',async({page})=>{
 await page.goto('/#interview');
 const card=page.locator('.exercise-card').filter({has:page.getByRole('heading',{name:'Reconcile the order mart',exact:true})});
 await card.getByRole('button',{name:'Open challenge ↗'}).click();
 await page.getByLabel('Clarification question').fill('Are child IDs unique?');
 await page.getByRole('button',{name:'Ask clarification →'}).click();
 await expect(page.getByText('order_id is unique in orders; payment_id and item_id are unique within their tables. An order can have many rows in each child.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Hint policy',exact:true}).click();
 await expect(page.locator('.notice[role=alert]')).toContainText('Hints are disabled');
 await expect(page.locator('.attempt-status')).toContainText('0 hints');
});

test('light theme and narrow layout keep solving controls usable',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'☼ Light appearance'}).click();
 await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Practice',exact:true}).click();
 await page.locator('.exercise-card').first().getByRole('button',{name:'Open challenge ↗'}).click();
 await expect(page.getByRole('button',{name:'▷ Run',exact:true})).toBeVisible();
 await expect(page.getByLabel('Assumptions & explanation',{exact:false})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
});

test('a stale second tab cannot silently replace the first tab draft',async({page,context})=>{
 await page.goto('/#library');
 await page.locator('.exercise-card').first().getByRole('button',{name:'Open challenge ↗'}).click();
 await expect(page.getByRole('textbox',{name:'SQL query editor',exact:true})).toBeVisible();
 const url=page.url(),id=url.split('attempt/')[1];
 const second=await context.newPage();await second.goto(url);
 await expect(second.getByRole('textbox',{name:'SQL query editor',exact:true})).toBeVisible();
 await writeSQL(page,'SELECT 101 AS first_tab');
 await expect.poll(async()=>{const a=await (await page.request.get('/api/attempts/'+id)).json();return a.code;}).toContain('first_tab');
 await writeSQL(second,'SELECT 202 AS second_tab');
 await expect(second.getByRole('status')).toContainText('changed in another request or tab');
 await second.getByRole('button',{name:'▷ Run',exact:true}).click();
 await expect(second.locator('.notice[role=alert]')).toContainText('Resolve this draft conflict');
 expect((await (await page.request.get('/api/attempts/'+id)).json()).code).toContain('first_tab');
 await second.reload();
 await expect(second.getByRole('button',{name:'Restore browser copy'})).toBeVisible();
 expect((await (await page.request.get('/api/attempts/'+id)).json()).code).toContain('first_tab');
 await second.close();
});
