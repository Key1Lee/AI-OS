import { readFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const load = async relative => JSON.parse(await readFile(path.join(root, relative), 'utf8'));
const workflow = await load('workflows/northstar-leadops.json');
const hot = await load('fixtures/01_hot_lead.json');
const node = name => {
  const found = workflow.nodes.find(item => item.name === name);
  if (!found) throw new Error(`Missing node: ${name}`);
  return found;
};
const run = (name, input) => new Function('$json', '$node', '$execution', node(name).parameters.jsCode)(
  input,
  { 'Validate & Normalize [D]': { json: { idempotency_key: 'website_demo:baseline_001' } } },
  { id: 'offline-regression' },
)[0].json;

const cases = [];
const check = (name, input, expected, actual, errorType) => {
  const pass = JSON.stringify(actual) === JSON.stringify(expected);
  cases.push({ name, pass, input, expected, actual, error_type: errorType,
    existed_before_change: null, caused_by_new_change: null });
};

const validInput = structuredClone(hot.input);
validInput.event_id = 'baseline_001';
validInput.source = ' WEBSITE_DEMO ';
validInput.lead.email = ' MAYA.CHEN@ACMEOPS.EXAMPLE ';
const valid = run('Validate & Normalize [D]', validInput);
check('valid normalization and event key', validInput,
  { valid: true, source: 'website_demo', email: 'maya.chen@acmeops.example', idempotency_key: 'website_demo:baseline_001' },
  { valid: valid.valid, source: valid.source, email: valid.email, idempotency_key: valid.idempotency_key },
  'none');

for (const [name, edit, error] of [
  ['missing email', input => delete input.lead.email, 'lead.email is invalid'],
  ['invalid email', input => { input.lead.email = 'not-an-email'; }, 'lead.email is invalid'],
  ['missing consent', input => delete input.lead.consent_to_contact, 'lead.consent_to_contact must be true'],
  ['missing event ID', input => delete input.event_id, 'event_id is required and must be <= 128 characters'],
]) {
  const input = structuredClone(validInput);
  edit(input);
  const output = run('Validate & Normalize [D]', input);
  check(name, input, { valid: false, error_present: true },
    { valid: output.valid, error_present: output.validation_errors.includes(error) },
    'validation');
}

for (const [name, input, expected] of [
  ['CRM 429', { error: { statusCode: 429, message: 'Rate limited' } }, { error_code: 'HUBSPOT_429', retryable: true }],
  ['CRM 500', { error: { statusCode: 500, message: 'Server error' } }, { error_code: 'HUBSPOT_500', retryable: true }],
  ['CRM 401', { error: { statusCode: 401, message: 'Unauthorized' } }, { error_code: 'HUBSPOT_401', retryable: false }],
  ['CRM 400', { error: { statusCode: 400, message: 'Bad request' } }, { error_code: 'HUBSPOT_400', retryable: false }],
  ['CRM timeout', { error: { message: 'timeout' } }, { error_code: 'CRM_OUTCOME_UNKNOWN', retryable: true }],
]) {
  const output = run('Normalize CRM Failure [D]', input);
  check(name, input, expected,
    { error_code: output.error_code, retryable: output.retryable }, 'crm_api');
}

check('contact create has no blind retry', { node: 'HubSpot - Create Contact Once' },
  { retryOnFail: false, onError: 'continueErrorOutput', verifyNode: true },
  { retryOnFail: node('HubSpot - Create Contact Once').retryOnFail === true,
    onError: node('HubSpot - Create Contact Once').onError,
    verifyNode: workflow.nodes.some(item => item.name === 'HubSpot - Verify Ambiguous Create') },
  'ambiguous_write');

check('Slack send has effect ledger', { node: 'Slack - Send Claimed Notification' },
  { claim: true, unknown: true, blindRetry: false },
  { claim: workflow.nodes.some(item => item.name === 'Postgres - Claim Notification Effect'),
    unknown: workflow.nodes.some(item => item.name === 'Postgres - Mark Notification Unknown'),
    blindRetry: node('Slack - Send Claimed Notification').retryOnFail === true },
  'ambiguous_write');

const failed = cases.filter(item => !item.pass);
console.log(`Offline baseline: ${cases.length - failed.length}/${cases.length} checks passed.`);
if (failed.length) {
  for (const item of failed) console.error(JSON.stringify({
    input: item.input, expected: item.expected, actual: item.actual,
    error_type: item.error_type, existed_before_change: item.existed_before_change,
    caused_by_new_change: item.caused_by_new_change, case: item.name,
  }));
  process.exitCode = 1;
}
