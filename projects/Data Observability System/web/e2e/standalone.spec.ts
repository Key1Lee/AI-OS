import {test,expect} from '@playwright/test';
import path from 'node:path';

test('independent map provides metadata, incident evidence and inert SQL without learner UI',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/');
 await expect(page.getByRole('button',{name:/^Expand /})).toHaveCount(5);
 await expect(page.getByRole('button',{name:'Start Assessment',exact:true})).toHaveCount(0);
 await expect(page.getByText('Saved investigations',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Show failure path',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Earliest observed anomaly: int order items'})).toBeVisible();
 await expect(page.getByText('First bad node cannot yet be established.',{exact:true})).toBeVisible();
 await page.screenshot({path:path.resolve('../docs/screenshots/standalone-incident.png'),fullPage:true});
 await page.getByRole('button',{name:'Open node int_order_items',exact:true}).click();
 await page.getByRole('tab',{name:'SQL',exact:true}).click();
 await expect(page.locator('.dm-code')).toContainText('LEFT JOIN');
 expect(await (await page.request.get('/api/map/investigations/current')).status()).toBe(404);
 expect(errors).toEqual([]);
});

test('independent import, keyboard stages and narrow light layout work',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/map');
 await page.getByRole('button',{name:'Change appearance',exact:true}).click();
 await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 const stage=page.getByRole('button',{name:'Expand Sources',exact:true});await stage.focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('button',{name:'Open node raw_orders',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
 await page.getByText('Import dbt artifact files',{exact:true}).click();
 await page.getByLabel('System ID',{exact:true}).fill('independent-import');
 const manifest={nodes:{'model.demo.one':{name:'one',resource_type:'model',raw_code:'SELECT 1'}}};
 await page.getByLabel('manifest.json (required)',{exact:true}).setInputFiles({name:'manifest.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(manifest))});
 await page.getByRole('button',{name:'Import metadata',exact:true}).click();
 await expect(page.getByRole('heading',{name:'My data system',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Expand Unclassified',exact:true}).click();
 await page.getByRole('button',{name:'Open node one',exact:true}).click();
 await expect(page.getByText('Primary key unknown',{exact:true})).toBeVisible();
 await page.screenshot({path:path.resolve('../docs/screenshots/standalone-mobile.png'),fullPage:true});
});
