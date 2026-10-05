import json
import sys
import subprocess
from pathlib import Path

sys.dont_write_bytecode = True
from lab.core import Lab
from lab.warehouse import Warehouse
from lab.fixtures import revenue

ROOT = Path(__file__).resolve().parents[1]

# Sandbox denies the tsx CLI's local IPC socket. Keep its TypeScript loader and
# actual native engine unchanged, but launch directly through Node's import hook.
native_subprocess_run = subprocess.run
def sandbox_run(command, *args, **kwargs):
    if isinstance(command, list) and command and str(command[0]).endswith('node_modules/.bin/tsx'):
        project = Path(command[0]).parents[2]
        command = ['node', '--import', str(project / 'node_modules/tsx/dist/loader.mjs'), *command[1:]]
    return native_subprocess_run(command, *args, **kwargs)
subprocess.run = sandbox_run

def summarize(phase):
    return {key: phase[key] for key in ('rows', 'expected_rows', 'revenue', 'expected_revenue', 'duplicate_extra', 'pipeline_status', 'model_status', 'quality_status', 'publication', 'dashboard', 'freshness')} | {
        'attempt_rows': [attempt['warehouse_rows_after_attempt'] for attempt in phase['attempts']],
        'attempt_status': [attempt['native']['status'] for attempt in phase['attempts']],
        'native_incidents': phase['observability']['incidents'],
        'impacted_outputs': phase['observability']['impact'],
        'native_model_failures': [test for result in phase['modeling']['results'] for test in result['evaluation']['tests'] if test['status'] != 'pass'],
        'native_quality_gate_states': [result['gate']['status'] for result in phase['quality']['results']],
        'execution_nodes': [execution['node_id'] for execution in phase['observability']['executions']],
        'lineage_edges': phase['observability']['lineage'],
        'model_actual_parents': [result['fact']['parents'] for result in phase['modeling']['results']],
    }

lab = Lab(ROOT / 'ae-native-trace-profile')
record = lab.run()
run_id = record['run_id']
summary = {'run_id': run_id, 'directory': str(lab.directory(record)), 'phases': {phase: summarize(record['phases'][phase]) for phase in ('baseline', 'fault')}}
assert summary['phases']['baseline']['rows'] == 1000
assert summary['phases']['fault']['attempt_rows'] == [700, 1700]
assert summary['phases']['fault']['quality_status'] == 'FAIL'
assert summary['phases']['fault']['publication'] == 'BLOCKED'
assert summary['phases']['fault']['impacted_outputs'] == ['executive_dashboard']
assert lab.answer(run_id, 'diagnose', {'layer': 'ingestion', 'property': 'idempotency', 'signal': 'duplicate_order_ids', 'reason': 'Recorded partial append is repeated on full retry'})['outcome'] == 'pass'
record = lab.fix(run_id)
record = lab.verify(run_id)
warehouse = Warehouse(lab.directory(record) / 'warehouse.sqlite')
assert warehouse.rows() == warehouse.rows('fct_orders') == sorted(lab.source(record), key=lambda row: row['order_id'])
assert record['verification']['status'] == 'PASS'
summary['phases'].update({phase: summarize(record['phases'][phase]) for phase in ('recovery', 'rerun')})
summary['verification'] = record['verification']
(ROOT / 'ae-native-order-trace.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'trace': str(ROOT / 'ae-native-order-trace.json'), 'run_id': run_id, 'baseline_revenue': summary['phases']['baseline']['revenue'], 'fault_revenue': summary['phases']['fault']['revenue'], 'retry_rows': summary['phases']['fault']['attempt_rows'], 'recovered_rows': record['phases']['recovery']['rows'], 'verification': record['verification']}))

class SilentCorruptionWarehouse(Warehouse):
    def write(self, orders, policy):
        super().write(orders, policy)
        with self.connect() as db:
            db.execute('UPDATE orders_raw SET amount_cents=amount_cents+100 WHERE order_id=?', ('O0001',))

silent_lab = Lab(ROOT / 'ae-silent-corruption-profile')
silent_record = silent_lab.start()
silent_dir = silent_lab.directory(silent_record)
silent_warehouse = SilentCorruptionWarehouse(silent_dir / 'warehouse.sqlite')
silent_result = silent_lab.phase(silent_record, 'baseline', silent_warehouse, 'upsert', None)
silent = {'run_id': silent_record['run_id'], 'directory': str(silent_dir), 'injection': 'real Warehouse.write followed by +100 cents mutation of O0001 orders_raw, all native adapters unchanged', **summarize(silent_result)}
assert silent['pipeline_status'] == 'SUCCESS'
assert silent['model_status'] == 'FAIL'
assert silent['quality_status'] == 'PASS'
assert silent['publication'] == 'ELIGIBLE'
assert silent['dashboard']['trusted'] is True
assert silent['revenue'] != silent['expected_revenue']
(ROOT / 'ae-silent-corruption.json').write_text(json.dumps(silent, indent=2) + '\n')
print(json.dumps({'silent_probe': str(ROOT / 'ae-silent-corruption.json'), 'pipeline_status': silent['pipeline_status'], 'model_status': silent['model_status'], 'quality_status': silent['quality_status'], 'publication': silent['publication'], 'dashboard': silent['dashboard'], 'expected_revenue': silent['expected_revenue'], 'observability_incidents': len(silent['native_incidents'])}))
