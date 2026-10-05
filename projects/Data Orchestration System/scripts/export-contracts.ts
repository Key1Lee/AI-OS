import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { executionEventSchema, scenarioSchema, scenarioContract, simulate, TODAY } from '../src/engine';
const directory = fileURLToPath(new URL('../contracts/', import.meta.url));
mkdirSync(directory, { recursive: true });
for (const [name, schema] of Object.entries({ 'execution-event.schema': executionEventSchema, 'scenario.schema': scenarioSchema })) {
  writeFileSync(`${directory}${name}.json`, JSON.stringify(schema, null, 2) + '\n');
}
const scenario = scenarioContract('transient');
writeFileSync(`${directory}example-scenario.json`, JSON.stringify(scenario, null, 2) + '\n');
writeFileSync(`${directory}example-execution.json`, JSON.stringify(simulate(scenario.workflow, { partition: TODAY }), null, 2) + '\n');
process.stdout.write('Exported two JSON Schemas and deterministic scenario/execution examples.\n');
