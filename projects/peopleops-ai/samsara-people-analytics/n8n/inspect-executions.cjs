// Read-only proof from this demo's n8n database; no credential or payload export.
const { DatabaseSync } = require('node:sqlite');
const { parse } = require('/usr/local/lib/node_modules/n8n/node_modules/flatted');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });
const executions = db.prepare('SELECT id, status, workflowId FROM execution_entity WHERE workflowId = ? ORDER BY id DESC LIMIT 15').all('samsaraSurveyDemo2026');
const results = executions.map(execution => {
  const row = db.prepare('SELECT data FROM execution_data WHERE executionId = ?').get(execution.id);
  const data = row ? parse(row.data) : {};
  return { ...execution, lastNodeExecuted: data.resultData?.lastNodeExecuted,
    nodes: Object.keys(data.resultData?.runData || {}) };
});
console.log(JSON.stringify({ timestamp: new Date().toISOString(), executions: results }, null, 2));
db.close();
