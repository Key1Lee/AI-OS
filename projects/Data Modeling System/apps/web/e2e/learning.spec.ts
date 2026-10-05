import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const screenshots = fileURLToPath(new URL('../../../docs/screenshots/', import.meta.url));
mkdirSync(screenshots,{recursive:true});
async function nav(page:Page, label:string) {
  await page.getByRole('navigation').getByRole('button',{name:new RegExp(label)}).click();
}
async function stage(page:Page) {
  await page.getByLabel('Source grain',{exact:true}).selectOption('source_order_version');
  await page.getByLabel('Source primary key',{exact:true}).selectOption('orderId,sourceVersion');
  await page.getByRole('button',{name:'Check my grain',exact:true}).click();
  await page.getByRole('button',{name:'Create staging model',exact:true}).click();
  await expect(page.locator('.inspector h3')).toHaveText('stg_orders');
}
async function build(page:Page) {
  await nav(page,'Build & verify');
  await page.getByLabel('Fact grain').selectOption('order');
  await page.getByLabel('Fact primary key').selectOption('order_id');
  await page.getByRole('button',{name:'Build & verify fact',exact:true}).click();
  await expect(page.getByText('All model assertions pass',{exact:true})).toBeVisible();
}
async function clickArrow(page:Page, source:string, target:string) {
  await page.locator('.flow-canvas').scrollIntoViewIfNeeded();
  const arrow=page.locator(`.react-flow__edge[data-id="${source}→${target}"] .react-flow__edge-textwrapper`);
  await expect(arrow).toBeVisible();
  await arrow.click();
}

test('complete grain → staging → join → fact → metric learning journey',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{level:1})).toContainText('From raw data');
  await expect(page.locator('.source-card')).toHaveCount(6);
  await page.screenshot({path:`${screenshots}/story-initial.png`,fullPage:true});
  await nav(page,'Build & verify');
  await expect(page.getByText('Start by declaring the source grain.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Build & verify fact',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Inspect source orders',exact:true}).click();
  await stage(page);
  await expect(page.getByRole('region',{name:'Transformation difference'})).toContainText('5');
  await nav(page,'Join lab');
  await expect(page.getByTestId('join-row-count')).toHaveText('4');
  await expect(page.getByTestId('joined-revenue')).toHaveText('$325.00');
  await page.getByLabel('Aggregate right side to its join key first').check();
  await expect(page.getByTestId('join-row-count')).toHaveText('3');
  await expect(page.getByTestId('joined-revenue')).toHaveText('$225.00');
  await build(page);
  await page.getByRole('button',{name:'Break it: join items',exact:true}).click();
  await expect(page.getByText('Model assertions failed',{exact:true})).toBeVisible();
  await expect(page.locator('.mini-stat-row')).toContainText('$325.00');
  await page.getByRole('button',{name:'Repair: preserve order grain',exact:true}).click();
  await expect(page.getByText('All model assertions pass',{exact:true})).toBeVisible();
  await nav(page,'Semantic metric');
  await page.getByRole('button',{name:'Calculate metric',exact:true}).click();
  await expect(page.getByTestId('metric-value')).toHaveText('$225.00');
  await expect(page.getByText('Matches expected metric',{exact:true})).toBeVisible();
  await page.screenshot({path:`${screenshots}/metric-verified.png`,fullPage:true});
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export evidence',exact:true}).click();
  const downloaded=await downloadPromise;
  const evidence=JSON.parse(readFileSync((await downloaded.path())!,'utf8'));
  expect(evidence.build.evaluation.status).toBe('pass');
  expect(evidence.metric.value).toBe('225.00');
  expect(evidence.definitions.contract_version).toBe('modeling-lab-v1');
  await page.getByRole('button',{name:'Reset session',exact:true}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Reset session',exact:true}).click();
  await expect(page.locator('.inspector')).toContainText('GRAIN UNKNOWN');
  expect(errors).toEqual([]);
});

test('wrong source grain is contradicted and redeclaration invalidates downstream evidence',async({page})=>{
  await page.goto('/');
  await page.getByLabel('Source grain',{exact:true}).selectOption('order');
  await page.getByLabel('Source primary key',{exact:true}).selectOption('orderId');
  await page.getByRole('button',{name:'Check my grain',exact:true}).click();
  await expect(page.locator('.inspector .grain-form')).toContainText('Fail');
  await expect(page.getByRole('button',{name:'Create staging model',exact:true})).toHaveCount(0);
  await stage(page);await build(page);
  await nav(page,'Transformation story');
  await page.locator('.source-card').filter({hasText:'orders'}).first().click();
  await page.getByLabel('Source grain',{exact:true}).selectOption('order');
  await page.getByLabel('Source primary key',{exact:true}).selectOption('orderId');
  await page.getByRole('button',{name:'Check my grain',exact:true}).click();
  await expect(page.locator('.model-node.fact')).toContainText('GRAIN UNKNOWN');
  await nav(page,'Build & verify');
  await expect(page.getByText('Start by declaring the source grain.',{exact:true})).toBeVisible();
});

test('join visual explanation follows actual per-key multiplicity, repairs, and NULL semantics',async({page})=>{
  await page.goto('/');await nav(page,'Join lab');
  await expect(page.getByTestId('joined-revenue')).toHaveText('$325.00');
  await expect(page.locator('.join-trace.repeated')).toHaveCount(1);
  await expect(page.locator('.join-trace.repeated .trace-outputs span')).toHaveCount(2);
  await page.screenshot({path:`${screenshots}/join-fanout.png`,fullPage:true});
  await page.getByLabel('Aggregate right side to its join key first').check();
  await expect(page.getByTestId('joined-revenue')).toHaveText('$225.00');
  await expect(page.getByTestId('join-row-count')).toHaveText('3');
  await page.screenshot({path:`${screenshots}/join-repaired.png`,fullPage:true});
  await page.getByLabel('Right dataset',{exact:true}).selectOption('customers');
  await expect(page.getByTestId('join-row-count')).toHaveText('3');
  await expect(page.locator('.revenue-comparison')).toContainText('already unique');
  const customerTrace=page.locator('.join-trace').filter({has:page.locator('.trace-source strong',{hasText:'C1'})});
  await expect(customerTrace.locator('.trace-outputs b')).toHaveCount(0);
  await expect(customerTrace.locator('.trace-contribution strong')).toHaveText('$150.00');
  await page.getByLabel('Left dataset',{exact:true}).selectOption('stg_orders');
  await expect(page.getByTestId('join-row-count')).toHaveText('4');
  await page.getByLabel('Join type',{exact:true}).selectOption('inner');
  await expect(page.getByTestId('join-row-count')).toHaveText('3');
  await expect(page.locator('.revenue-comparison')).toContainText('INNER removed 1');
  await expect(page.locator('.trace-outputs')).toContainText(['','', 'removed by INNER']);
});

test('advanced equivalent SQL and each actual parent arrow expose the correct input',async({page})=>{
  await page.goto('/');await stage(page);await build(page);
  await page.getByRole('button',{name:'Advanced',exact:true}).click();
  await page.getByLabel('Fact SQL').fill("SELECT o.*, c.name AS customer_name FROM stg_orders o LEFT JOIN customers c ON o.customer_id=c.customer_id WHERE o.status='completed' ORDER BY order_id DESC");
  await expect(page.getByText(/Draft changed/)).toBeVisible();
  await page.getByRole('button',{name:'Build & verify fact',exact:true}).click();
  await expect(page.getByText('All model assertions pass',{exact:true})).toBeVisible();
  await nav(page,'Transformation story');
  await clickArrow(page,'stg_orders','fct_orders');
  await expect(page.getByRole('region',{name:'Transformation difference'}).locator('.before-after strong').first()).toHaveText('stg_orders');
  await clickArrow(page,'customers','fct_orders');
  await expect(page.getByRole('region',{name:'Transformation difference'}).locator('.before-after strong').first()).toHaveText('customers');
});

test('metric aggregation mistakes are evaluated and can be repaired',async({page})=>{
  await page.goto('/');await stage(page);await build(page);await nav(page,'Semantic metric');
  await page.getByLabel('Metric aggregation').selectOption('AVG');
  await page.getByRole('button',{name:'Calculate metric',exact:true}).click();
  await expect(page.getByTestId('metric-value')).toHaveText('$75.00');
  await expect(page.getByText('Does not match Revenue definition',{exact:true})).toBeVisible();
  await page.getByLabel('Metric aggregation').selectOption('SUM');
  await page.getByRole('button',{name:'Calculate metric',exact:true}).click();
  await expect(page.getByTestId('metric-value')).toHaveText('$225.00');
});

test('many-to-many item/payment experiment exposes the multiplicative join',async({page})=>{
  await page.goto('/');await nav(page,'Join lab');
  await page.getByLabel('Left dataset',{exact:true}).selectOption('order_items');
  await expect(page.getByTestId('join-row-count')).toHaveText('8');
  await expect(page.locator('.join-stat-grid')).toContainText('N:N');
  const order=page.locator('.join-trace').filter({has:page.locator('.trace-source strong',{hasText:'O1'})});
  await expect(order.locator('.trace-outputs span')).toHaveCount(4);
  await expect(order.locator('.trace-source')).toContainText('2 left rows');
  await expect(order.locator('.trace-operation')).toContainText('2 matches');
  await expect(page.getByText('Amounts vary across these left rows; total is shown at right.',{exact:true})).toHaveCount(0);
  await page.getByLabel('Aggregate right side to its join key first').check();
  await expect(page.getByTestId('join-row-count')).toHaveText('5');
  await expect(page.locator('.join-stat-grid')).toContainText('N:1');
  await expect(page.getByLabel('Expected cardinality')).toHaveValue('N:1');
  await expect(page.locator('.join-outcome')).toContainText('GRAIN PRESERVED');
});

test('narrow viewport keeps the full learner workflow usable without page overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');await expect(page.locator('.source-card')).toHaveCount(6);
  await page.screenshot({path:`${screenshots}/story-mobile.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await stage(page);await build(page);await nav(page,'Semantic metric');
  await page.getByRole('button',{name:'Calculate metric',exact:true}).click();
  await expect(page.getByTestId('metric-value')).toHaveText('$225.00');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
