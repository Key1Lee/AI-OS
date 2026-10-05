"""Independent verifier probes. This file is not the product test suite.

Run: uv run python docs/verification-evidence/core-probes.py
Only writes its own evidence JSON beside this file.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, Inexact, ROUND_DOWN, ROUND_UP, localcontext
import hashlib
import json
from pathlib import Path
import runpy
import sys

from fastapi.testclient import TestClient
from pydantic import ValidationError

from quality_system.adapters import contract_from_modeling, dbt_export, dbt_result, observability_test
from quality_system.api import create_app
from quality_system.compatibility import CompatibilityPolicy, CompatibilityRequest, compare_contracts
from quality_system.contracts import (AcceptedValues, Business, Column, DataContract, Dataset, Freshness,
    NotNull, QualityRule, Reconciliation, Relationship, Schema, Unique, ValidateRequest, Volume)
from quality_system.engine import compile_contract, money, quality_gate, validate, validate_bundle, value_matches
from quality_system.scenarios import BASE_CLOCK, ScenarioRequest, data_contract, fixture, scenario_input

ROOT = Path(__file__).resolve().parents[2]
START_HASHES = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / 'src/quality_system').glob('*.py')}
REPORTS = []
ORIGINAL = scenario_input(ScenarioRequest())
BASE = validate_bundle(ORIGINAL)
RULES = {r.id: r for r in BASE.rules}
DIMENSIONS = {'unique': 'uniqueness', 'not_null': 'completeness', 'accepted_values': 'validity',
    'relationship': 'referential_integrity', 'schema': 'schema', 'business_rule': 'business_rule',
    'freshness': 'freshness', 'volume': 'volume', 'reconciliation': 'reconciliation'}


def check(id, group, operation, expected, matcher=None):
    try:
        actual = operation()
        supported = (matcher(actual) if matcher else actual == expected)
        REPORTS.append({'id': id, 'group': group, 'supported': bool(supported), 'expected': expected, 'actual': actual})
    except Exception as exc:
        REPORTS.append({'id': id, 'group': group, 'supported': False, 'expected': expected,
            'actual': {'exception': type(exc).__name__, 'message': str(exc)}})


def rule(expectation, severity='CRITICAL', blocking=True):
    return QualityRule(id='independent_probe', name='Independent probe', description='An independent, controlled edge case.',
        target='fct_orders', dimension=DIMENSIONS[expectation.kind], expectation=expectation,
        severity=severity, blocking=blocking)


def run(expectation, rows, *, parent=None, columns=None, loaded_at=None, severity='CRITICAL', blocking=True):
    datasets = {'fct_orders': Dataset(id='fct_orders', rows=deepcopy(rows), columns=columns,
        loaded_at=loaded_at, currency='USD')}
    if parent is not None:
        datasets.update(parent)
    return validate(rule(expectation, severity, blocking), datasets, ORIGINAL.contract, BASE_CLOCK, 'probe', 'probe')


def status(expectation, rows, **kwargs):
    return run(expectation, rows, **kwargs).status


def gate(**updates):
    context = {'dataset_id': 'fct_orders', 'rules': BASE.rules, 'results': BASE.results,
        'run_id': BASE.run_id, 'input_fingerprint': BASE.input_fingerprint, 'executed_at': BASE_CLOCK}
    context.update(updates)
    return quality_gate(**context).status


def compatibility(mutator, policy=None, compatible_data=None):
    before = data_contract()
    after = before.model_copy(deep=True)
    mutator(after)
    return compare_contracts(CompatibilityRequest(before=before, after=after,
        policy=policy or CompatibilityPolicy(), compatible_data=compatible_data))['status']


def recon(target, source, adjustment=None, absolute='0.01', relative='0'):
    def row(amount, status=None):
        payload = {'net_revenue': amount, 'amount': amount, 'refund_amount': amount, 'currency': 'USD'}
        if status is not None:
            payload['status'] = status
        return payload
    datasets = {
        'fct_orders': Dataset(id='fct_orders', rows=[row(x) for x in target], currency='USD'),
        'payments': Dataset(id='payments', rows=[row(x, 'captured') for x in source], currency='USD'),
        'returns': Dataset(id='returns', rows=[row(x, 'refunded') for x in (adjustment or [])], currency='USD'),
    }
    return validate(rule(Reconciliation(absolute_tolerance=absolute, relative_tolerance=relative)),
        datasets, ORIGINAL.contract, BASE_CLOCK, 'probe', 'probe')


def rate_at_precision(precision):
    with localcontext() as ctx:
        ctx.prec = precision
        return run(NotNull(column='x', minimum_rate='0.333333333333333333333333333333'),
            [{'x': 1}, {'x': None}, {'x': None}]).model_dump(mode='json')


def rate_at_rounding(rounding):
    with localcontext() as ctx:
        ctx.rounding = rounding
        return run(NotNull(column='x', minimum_rate='0.5'), [{'x': 1}, {'x': None}, {'x': None}]).model_dump(mode='json')


def rate_with_inexact_trap():
    with localcontext() as ctx:
        ctx.traps[Inexact] = True
        return run(NotNull(column='x', minimum_rate='0.5'), [{'x': 1}, {'x': None}, {'x': None}]).status


def wrong_gate_target():
    try:
        return gate(dataset_id='mart_revenue')
    except ValueError:
        return 'REJECTED'


def compile_long_name():
    name = 'x' * 80
    contract = DataContract(id='long_name', dataset_id='long_name', grain='one row per key', primary_key=[name],
        columns=[Column(name=name, data_type='STRING', nullable=False)], owner='Verifier', semantic_meaning='A controlled contract.')
    return len(compile_contract(contract))


def integer_widening_sound():
    before = data_contract()
    before.columns.append(Column(name='units', data_type='INTEGER', nullable=False))
    after = before.model_copy(deep=True)
    after.columns[-1].data_type = 'DECIMAL'
    after.columns[-1].precision = 21
    after.columns[-1].scale = 2
    classification = compare_contracts(CompatibilityRequest(before=before, after=after,
        policy=CompatibilityPolicy(allow_type_widening=True)))['status']
    return {'before_accepts_large': value_matches(10 ** 30, before.columns[-1]),
        'after_accepts_large': value_matches(10 ** 30, after.columns[-1]), 'compatibility': classification}


check('baseline-18-pass', 'scenario', lambda: BASE.summary, {'PASS': 18, 'WARN': 0, 'FAIL': 0, 'UNKNOWN': 0})
check('baseline-gate-open', 'gate', gate, 'OPEN')
check('fixture-exact-sums', 'scenario', lambda: [str(sum((Decimal(r['net_revenue']) for r in ORIGINAL.datasets['fct_orders'].rows), Decimal(0))),
    str(sum((Decimal(r['amount']) for r in ORIGINAL.datasets['payments'].rows), Decimal(0))),
    str(sum((Decimal(r['refund_amount']) for r in ORIGINAL.datasets['returns'].rows), Decimal(0)))], ['550.00', '555.00', '5.00'])
check('scenario-input-immutable', 'determinism', lambda: validate_bundle(ORIGINAL).model_dump(mode='json') == BASE.model_dump(mode='json'), True)
check('fixture-isolation', 'determinism', lambda: (scenario_input(ScenarioRequest(corruptions=['duplicate'])), len(fixture()['fct_orders'].rows))[1], 10)
for corruption, expected_failure in [('duplicate', 'contract_grain'), ('orphan', 'relationship_0_customer_id'),
        ('schema', 'contract_schema'), ('stale', 'freshness'), ('unpaid', 'completed_paid')]:
    check('failure-' + corruption, 'scenario', lambda c=corruption, f=expected_failure:
        [validate_bundle(scenario_input(ScenarioRequest(corruptions=[c]))).gate.status,
         next(r.status for r in validate_bundle(scenario_input(ScenarioRequest(corruptions=[c]))).results if r.rule_id == f)], ['BLOCKED', 'FAIL'])
check('warning-continues', 'gate', lambda: [validate_bundle(scenario_input(ScenarioRequest(corruptions=['warning']))).gate.status,
    validate_bundle(scenario_input(ScenarioRequest(corruptions=['warning']))).summary], ['OPEN', {'PASS': 17, 'WARN': 1, 'FAIL': 0, 'UNKNOWN': 0}])

check('unique-composite', 'uniqueness', lambda: status(Unique(columns=['x', 'y']), [{'x': 1, 'y': 2}, {'x': 1, 'y': 3}]), 'PASS')
check('unique-composite-repeat', 'uniqueness', lambda: run(Unique(columns=['x', 'y']), [{'x': 1, 'y': 2}, {'x': 1, 'y': 2}]).actual['duplicate_extra_rows'], 1)
check('unique-affected-vs-excess', 'uniqueness', lambda: [run(Unique(columns=['x']), [{'x': 'a'}] * 3).failed_rows,
    run(Unique(columns=['x']), [{'x': 'a'}] * 3).actual['duplicate_extra_rows']], [3, 2])
check('unique-typed-values', 'uniqueness', lambda: status(Unique(columns=['x']), [{'x': 1}, {'x': True}, {'x': '1'}]), 'PASS')
check('unique-null-fails', 'uniqueness', lambda: status(Unique(columns=['x']), [{'x': None}, {'x': 'a'}]), 'FAIL')
check('unique-null-ignore', 'uniqueness', lambda: status(Unique(columns=['x'], null_policy='ignore'), [{'x': None}, {'x': 'a'}]), 'PASS')
check('unique-all-null-ignore', 'unknown', lambda: status(Unique(columns=['x'], null_policy='ignore'), [{'x': None}]), 'UNKNOWN')
check('unique-empty', 'unknown', lambda: status(Unique(columns=['x']), []), 'UNKNOWN')
check('unique-missing-column', 'unknown', lambda: status(Unique(columns=['x']), [{'y': 1}]), 'UNKNOWN')
check('sample-row-number-protected', 'evidence', lambda: run(Unique(columns=['x']), [{'x': 'a', '_row_number': 999}, {'x': 'a'}]).evidence.sample_rows[0]['_row_number'], 1)
check('nonnull-zero-false-empty-string', 'completeness', lambda: status(NotNull(column='x'), [{'x': 0}, {'x': False}, {'x': ''}]), 'PASS')
check('nonnull-inclusive-threshold', 'completeness', lambda: status(NotNull(column='x', minimum_rate='0.75'), [{'x': 1}] * 3 + [{'x': None}]), 'PASS')
check('nonnull-below-threshold', 'completeness', lambda: status(NotNull(column='x', minimum_rate='0.7501'), [{'x': 1}] * 3 + [{'x': None}]), 'FAIL')
check('nonnull-exact-third-threshold', 'completeness', lambda: rate_at_precision(28)['status'], 'PASS')
check('nonnull-independent-of-decimal-context', 'determinism', lambda: rate_at_precision(28) == rate_at_precision(60), True)
check('nonnull-independent-of-rounding', 'determinism', lambda: rate_at_rounding(ROUND_DOWN) == rate_at_rounding(ROUND_UP), True)
check('nonnull-independent-of-inexact-trap', 'determinism', rate_with_inexact_trap, 'FAIL')
check('accepted-typed-membership', 'validity', lambda: status(AcceptedValues(column='x', values=[1]), [{'x': True}]), 'FAIL')
check('accepted-null-policy', 'validity', lambda: [status(AcceptedValues(column='x', values=['a']), [{'x': None}]),
    status(AcceptedValues(column='x', values=['a'], allow_null=True), [{'x': None}])], ['FAIL', 'PASS'])
check('accepted-invalid-value', 'validity', lambda: status(AcceptedValues(column='x', values=['a']), [{'x': 'b'}]), 'FAIL')

parents = {'customers': Dataset(id='customers', rows=[{'customer_id': 'C1'}])}
rel = Relationship(column='customer_id', parent_dataset='customers', parent_column='customer_id')
check('relationship-orphan', 'relationship', lambda: status(rel, [{'customer_id': 'C999'}], parent=parents), 'FAIL')
check('relationship-missing-parent', 'unknown', lambda: status(rel, [{'customer_id': 'C1'}]), 'UNKNOWN')
check('relationship-empty-parent', 'relationship', lambda: status(rel, [{'customer_id': 'C1'}], parent={'customers': Dataset(id='customers', rows=[])}), 'FAIL')
check('relationship-optional-null', 'relationship', lambda: status(rel.model_copy(update={'allow_null': True}), [{'customer_id': None}], parent=parents), 'PASS')
check('relationship-required-null', 'relationship', lambda: status(rel, [{'customer_id': None}], parent=parents), 'FAIL')
check('relationship-unknown-member', 'relationship', lambda: status(rel, [{'customer_id': 'UNKNOWN'}], parent={'customers': Dataset(id='customers', rows=[{'customer_id': 'UNKNOWN'}])}), 'PASS')
check('relationship-late-dimension-tolerance', 'relationship', lambda: status(rel.model_copy(update={'maximum_orphan_rate': Decimal('0.5')}),
    [{'customer_id': 'C1'}, {'customer_id': 'C999'}], parent=parents), 'PASS')
check('relationship-duplicate-parent', 'relationship', lambda: status(rel, [{'customer_id': 'C1'}], parent={'customers': Dataset(id='customers', rows=[{'customer_id': 'C1'}] * 2)}), 'FAIL')
check('relationship-duplicate-parent-opt-out', 'relationship', lambda: status(rel.model_copy(update={'require_unique_parent': False}),
    [{'customer_id': 'C1'}], parent={'customers': Dataset(id='customers', rows=[{'customer_id': 'C1'}] * 2)}), 'PASS')

check('schema-no-metadata', 'unknown', lambda: status(Schema(), ORIGINAL.datasets['fct_orders'].rows), 'UNKNOWN')
schema_cols = ORIGINAL.datasets['fct_orders'].columns
check('schema-missing-column', 'schema', lambda: status(Schema(), ORIGINAL.datasets['fct_orders'].rows, columns=[c for c in schema_cols if c.name != 'ordered_at']), 'FAIL')
check('schema-observed-nullable', 'schema', lambda: status(Schema(), ORIGINAL.datasets['fct_orders'].rows,
    columns=[c.model_copy(update={'nullable': True}) if c.name == 'order_id' else c for c in schema_cols]), 'FAIL')
bad_schema_rows = deepcopy(ORIGINAL.datasets['fct_orders'].rows)
bad_schema_rows[0]['net_revenue'] = 10.0
check('schema-rejects-float-money', 'schema', lambda: status(Schema(), bad_schema_rows, columns=schema_cols), 'FAIL')
check('schema-decimal-shape', 'schema', lambda: status(Schema(), ORIGINAL.datasets['fct_orders'].rows,
    columns=[c.model_copy(update={'scale': 3}) if c.name == 'net_revenue' else c for c in schema_cols]), 'FAIL')
check('money-38-digit-exact', 'money', lambda: str(money('99999999999999999999999999999999999999')), '99999999999999999999999999999999999999')
check('decimal38-schema-valid', 'money', lambda: value_matches('99999999999999999999999999999999999999',
    Column(name='big', data_type='DECIMAL', nullable=False, precision=38, scale=0)), True)
check('generated-id-name-boundary', 'contracts', compile_long_name, 3)

for label, loaded, expected_status in [('exact', '2026-10-01T22:00:00Z', 'PASS'),
    ('over', '2026-10-01T21:59:59.999999Z', 'FAIL'), ('future', '2026-10-02T00:00:01Z', 'UNKNOWN'),
    ('naive', '2026-10-01T22:00:00', 'UNKNOWN'), ('missing', None, 'UNKNOWN'),
    ('timezone', '2026-10-02T07:00:00+09:00', 'PASS')]:
    check('freshness-' + label, 'freshness', lambda stamp=loaded: status(Freshness(maximum_age_minutes=120), [{'x': 1}], loaded_at=stamp), expected_status)
check('volume-empty-fails', 'volume', lambda: status(Volume(minimum=1, maximum=3), []), 'FAIL')
check('volume-inclusive', 'volume', lambda: status(Volume(minimum=1, maximum=3), [{'x': 1}] * 3), 'PASS')
check('business-completed-unpaid', 'business', lambda: status(Business(invariant='completed_is_paid'), [{'status': 'completed', 'payment_status': 'unpaid'}]), 'FAIL')
check('business-noncomplete-unpaid', 'business', lambda: status(Business(invariant='completed_is_paid'), [{'status': 'pending', 'payment_status': 'unpaid'}]), 'PASS')
check('business-missing-evidence', 'unknown', lambda: status(Business(invariant='completed_is_paid'), [{'status': 'completed'}]), 'UNKNOWN')
check('business-shipment-before', 'business', lambda: status(Business(invariant='shipment_after_order'),
    [{'status': 'shipped', 'ordered_at': BASE_CLOCK, 'shipped_at': '2026-10-01T23:59:59Z'}]), 'FAIL')
check('business-shipped-null', 'business', lambda: status(Business(invariant='shipment_after_order'), [{'status': 'shipped', 'ordered_at': BASE_CLOCK, 'shipped_at': None}]), 'FAIL')
check('business-negative', 'business', lambda: status(Business(invariant='non_negative_revenue'), [{'net_revenue': '-0.01'}]), 'FAIL')
check('business-zero', 'business', lambda: status(Business(invariant='non_negative_revenue'), [{'net_revenue': '0.00'}]), 'PASS')

check('reconciliation-decimal-addition', 'reconciliation', lambda: recon(['0.30'], ['0.10', '0.20'], absolute='0').status, 'PASS')
check('reconciliation-absolute-equality', 'reconciliation', lambda: recon(['100.01'], ['100'], absolute='0.01').status, 'PASS')
check('reconciliation-over-tolerance', 'reconciliation', lambda: recon(['100.010000000000000001'], ['100'], absolute='0.01').status, 'FAIL')
check('reconciliation-relative-equality', 'reconciliation', lambda: recon(['101'], ['100'], absolute='0', relative='0.01').status, 'PASS')
check('reconciliation-exact-relative-third', 'reconciliation', lambda: recon(['4'], ['3'], absolute='0', relative='0.' + '3' * 38).status, 'FAIL')
check('reconciliation-zero-both', 'reconciliation', lambda: recon(['0'], ['0'], absolute='0').status, 'PASS')
check('reconciliation-zero-baseline', 'reconciliation', lambda: [recon(['1'], ['0'], absolute='0', relative='1').status,
    recon(['1'], ['0'], absolute='0', relative='1').actual['relative_difference']], ['FAIL', None])
check('reconciliation-refunds', 'reconciliation', lambda: recon(['90'], ['100'], ['10'], absolute='0').status, 'PASS')
check('reconciliation-nonfinite', 'unknown', lambda: recon(['NaN'], ['0']).status, 'UNKNOWN')

check('gate-wrong-dataset', 'gate', wrong_gate_target, 'BLOCKED or REJECTED', lambda value: value in {'BLOCKED', 'REJECTED'})
check('gate-missing', 'gate', lambda: gate(results=BASE.results[1:]), 'BLOCKED')
check('gate-duplicate', 'gate', lambda: gate(results=BASE.results + [BASE.results[0]]), 'BLOCKED')
for field, value in [('run_id', 'wrong'), ('input_fingerprint', 'wrong'), ('executed_at', '2026-10-02T01:00:00Z'),
    ('target_id', 'mart_revenue'), ('severity', 'WARNING'), ('blocking', False), ('status', 'UNKNOWN')]:
    altered = [r.model_copy(update={field: value}) if r.rule_id == BASE.results[0].rule_id else r for r in BASE.results]
    check('gate-mismatch-' + field, 'gate', lambda results=altered: gate(results=results), 'BLOCKED')
check('blocking-warning-blocks', 'gate', lambda: validate_bundle(scenario_input(ScenarioRequest(
    additional_rules=[rule(NotNull(column='description', minimum_rate='1'), severity='WARNING')], corruptions=['warning']))).gate.status, 'BLOCKED')
check('partial-selection-withholds', 'gate', lambda: validate_bundle(scenario_input(ScenarioRequest(rule_ids=['contract_grain']))).gate.status, 'BLOCKED')

check('compatibility-no-change', 'compatibility', lambda: compatibility(lambda c: None), 'COMPATIBLE')
check('compatibility-optional-add', 'compatibility', lambda: compatibility(lambda c: c.columns.append(Column(name='new_optional', data_type='STRING', nullable=True, required=False))), 'COMPATIBLE')
check('compatibility-strict-add', 'compatibility', lambda: compatibility(lambda c: c.columns.append(Column(name='new_optional', data_type='STRING', nullable=True, required=False)),
    CompatibilityPolicy(allow_optional_additions=False)), 'BREAKING')
check('compatibility-column-drop', 'compatibility', lambda: compatibility(lambda c: setattr(c, 'columns', [x for x in c.columns if x.name != 'ordered_at'])), 'BREAKING')
check('compatibility-type-change', 'compatibility', lambda: compatibility(lambda c: setattr(c.columns[1], 'data_type', 'INTEGER')), 'BREAKING')
check('compatibility-integer-widening-domain', 'compatibility', integer_widening_sound,
    'An additive type transition cannot reject values admitted by its prior domain',
    lambda value: not value['before_accepts_large'] or value['after_accepts_large'] or value['compatibility'] != 'COMPATIBLE')
check('compatibility-grain', 'compatibility', lambda: compatibility(lambda c: setattr(c, 'grain', 'one row per item')), 'BREAKING')
check('compatibility-key', 'compatibility', lambda: compatibility(lambda c: setattr(c, 'primary_key', ['customer_id'])), 'BREAKING')
check('compatibility-semantic', 'compatibility', lambda: compatibility(lambda c: setattr(c, 'semantic_meaning', 'Gross rather than net revenue')), 'BREAKING')
check('compatibility-semantic-review-policy', 'compatibility', lambda: compatibility(lambda c: setattr(c, 'semantic_meaning', 'Gross rather than net revenue'),
    CompatibilityPolicy(semantic_change='review')), 'REVIEW')
check('compatibility-null-tighten-no-proof', 'compatibility', lambda: compatibility(lambda c: setattr(c.columns[6], 'nullable', False)), 'BREAKING')
check('compatibility-null-tighten-with-proof', 'compatibility', lambda: compatibility(lambda c: setattr(c.columns[6], 'nullable', False), compatible_data=ORIGINAL.datasets['fct_orders']), 'COMPATIBLE')
check('compatibility-null-tighten-wrong-target', 'compatibility', lambda: compatibility(lambda c: setattr(c.columns[6], 'nullable', False),
    compatible_data=ORIGINAL.datasets['fct_orders'].model_copy(update={'id': 'other'})), 'BREAKING')
check('compatibility-null-tighten-empty', 'compatibility', lambda: compatibility(lambda c: setattr(c.columns[6], 'nullable', False),
    compatible_data=ORIGINAL.datasets['fct_orders'].model_copy(update={'rows': []})), 'BREAKING')

for invalid in [-1, True, '1', 1.5]:
    check('dbt-invalid-count-' + repr(invalid), 'adapter', lambda count=invalid: dbt_result(RULES['contract_grain'],
        {'status': 'pass', 'quality_rule_id': 'contract_grain', 'failures': count}, BASE_CLOCK, 'probe', 'probe').status, 'UNKNOWN')
check('dbt-zero-pass', 'adapter', lambda: dbt_result(RULES['contract_grain'], {'status': 'pass', 'quality_rule_id': 'contract_grain', 'failures': 0}, BASE_CLOCK, 'probe', 'probe').status, 'PASS')
check('dbt-wrong-rule', 'adapter', lambda: dbt_result(RULES['contract_grain'], {'status': 'pass', 'quality_rule_id': 'other', 'failures': 0}, BASE_CLOCK, 'probe', 'probe').status, 'UNKNOWN')
check('dbt-runtime-error', 'adapter', lambda: dbt_result(RULES['contract_grain'], {'status': 'error', 'quality_rule_id': 'contract_grain'}, BASE_CLOCK, 'probe', 'probe').status, 'UNKNOWN')
modeling_export = json.loads((ROOT.parent / 'Data Modeling System/docs/contracts.json').read_text())
check('modeling-actual-scenario-export', 'adapter', lambda: contract_from_modeling(modeling_export['scenario']).primary_key, ['order_id'])
check('modeling-preserves-business-definition', 'adapter', lambda: contract_from_modeling(modeling_export['scenario']).semantic_meaning == modeling_export['scenario']['fact_contract']['semantic_meaning'], True)
observability_contract = runpy.run_path(str(ROOT.parent / 'Data Observability System/src/data_system_map/contracts.py'))['TestResult']
check('observability-existing-shape', 'adapter', lambda: observability_contract.model_validate(observability_test(BASE.events[0], 'schema')).status, 'HEALTHY')
for incoming, outgoing in [('PASS', 'HEALTHY'), ('WARN', 'WARNING'), ('FAIL', 'FAILED'), ('UNKNOWN', 'UNKNOWN')]:
    check('observability-status-' + incoming, 'adapter', lambda a=incoming: observability_test(BASE.events[0].model_copy(update={'status': a}), 'test')['status'], outgoing)

client = TestClient(create_app())
check('api-missing-target-unknown-withheld', 'api', lambda: [client.post('/api/validate', json={**ORIGINAL.model_dump(mode='json'), 'datasets': {}}).json()['summary'],
    client.post('/api/validate', json={**ORIGINAL.model_dump(mode='json'), 'datasets': {}}).json()['gate']['status']],
    [{'PASS': 0, 'WARN': 0, 'FAIL': 0, 'UNKNOWN': 18}, 'BLOCKED'])
check('api-unknown-scenario', 'api', lambda: client.get('/api/scenarios/absent').status_code, 404)
check('api-invalid-clock-rejected', 'api', lambda: client.post('/api/validate', json={**ORIGINAL.model_dump(mode='json'), 'executed_at': '2026-10-02T00:00:00'}).status_code, 422)
check('api-rule-selection-rejected', 'api', lambda: client.post('/api/validate', json={**ORIGINAL.model_dump(mode='json'), 'rule_ids': ['absent']}).status_code, 422)
check('api-scoring-extension-rejected', 'boundary', lambda: client.post('/api/validate', json={**ORIGINAL.model_dump(mode='json'), 'score': 100}).status_code, 422)
check('api-deterministic-repeat', 'determinism', lambda: client.post('/api/validate', json=ORIGINAL.model_dump(mode='json')).content == client.post('/api/validate', json=ORIGINAL.model_dump(mode='json')).content, True)

hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / 'src/quality_system').glob('*.py')}
output = {'source_hashes_at_start': START_HASHES, 'source_hashes_at_end': hashes,
    'source_changed_during_run': START_HASHES != hashes,
    'probes': REPORTS, 'supported': sum(x['supported'] for x in REPORTS),
    'contradicted': sum(not x['supported'] for x in REPORTS)}
report_path = Path(__file__).with_name('core-probes.json')
report_path.write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + '\n')
for item in REPORTS:
    if not item['supported']:
        print(json.dumps(item, sort_keys=True, default=str))
print(json.dumps({'probes': len(REPORTS), 'supported': output['supported'], 'contradicted': output['contradicted'], 'evidence': str(report_path)}))
sys.exit(bool(output['contradicted']))
