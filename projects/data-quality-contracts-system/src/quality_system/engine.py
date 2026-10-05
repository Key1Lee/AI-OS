from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import hashlib
import json
from typing import Any

from .contracts import (Business, Column, DataContract, Dataset, Evidence, QualityEvent,
                        QualityGate, QualityRule, Schema, Unique, NotNull, ValidateRequest,
                        ValidationBundle, ValidationResult, aware)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(request: ValidateRequest, rules: list[QualityRule]) -> str:
    payload = {"contract": request.contract.model_dump(mode="json"),
               "datasets": {k: v.model_dump(mode="json") for k, v in request.datasets.items()},
               "rules": [r.model_dump(mode="json") for r in rules], "executed_at": request.executed_at}
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def bounded_id(value: str) -> str:
    return value if len(value) <= 80 else value[:59] + "_" + hashlib.sha256(value.encode()).hexdigest()[:20]


def decimal_context() -> Context:
    return Context(prec=100, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def compile_contract(contract: DataContract) -> list[QualityRule]:
    def rule(id, name, description, dimension, expectation):
        return QualityRule(id=bounded_id(id), name=name, description=description, target=contract.dataset_id,
                           dimension=dimension, expectation=expectation, owner=contract.owner)
    rules = [rule("contract_schema", "Schema matches the contract",
                  "Required columns, types and nullability preserve the producer's promise.",
                  "schema", Schema()),
             rule("contract_grain", "Primary key supports declared grain",
                  f"{contract.grain}. Repeating this key can repeat measures; uniqueness supports this declaration but does not prove row meaning.",
                  "uniqueness", Unique(columns=contract.primary_key))]
    rules += [rule(f"required_{c.name}", f"{c.name} is not null",
                   f"The contract requires a value in {c.name} for every row.",
                   "completeness", NotNull(column=c.name)) for c in contract.columns if c.required and not c.nullable]
    rules += [rule(f"relationship_{i}_{r.column}", f"{r.column} has a parent",
                   f"Every applicable {r.column} must exist in {r.parent_dataset}.{r.parent_column}.",
                   "referential_integrity", r) for i, r in enumerate(contract.relationships)]
    rules += contract.rules
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("A contract rule collides with a generated rule ID")
    return rules


def money(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Money requires a decimal string or integer; floats are not exact evidence")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal value") from exc
    if not parsed.is_finite() or parsed.copy_abs() >= Decimal("1e38") or parsed.as_tuple().exponent < -18:
        raise ValueError("Decimal must be finite and fit supported precision")
    return parsed


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")
    aware(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def value_matches(value: Any, column: Column) -> bool:
    if value is None:
        return column.nullable
    if column.data_type == "STRING":
        return isinstance(value, str)
    if column.data_type == "INTEGER":
        return type(value) is int and -(2 ** 63) <= value < 2 ** 63
    if column.data_type == "BOOLEAN":
        return type(value) is bool
    if column.data_type == "TIMESTAMP":
        try:
            timestamp(value)
            return True
        except ValueError:
            return False
    try:
        parsed = money(value)
        quantum = Decimal(1).scaleb(-column.scale)
        with localcontext(decimal_context()):
            return parsed == parsed.quantize(quantum) and abs(parsed) < Decimal(10) ** (column.precision - column.scale)
    except (ValueError, InvalidOperation):
        return False


def typed_key(values: list[Any]) -> str:
    if any(v is not None and type(v) not in (str, int, bool) for v in values):
        raise ValueError("Keys and categories must be scalar strings, integers or booleans")
    return canonical([[type(v).__name__, v] for v in values])


def _samples(rows, indexes):
    return [{**rows[i], "_row_number": i + 1} for i in sorted(indexes)[:8]]


def validate(rule: QualityRule, datasets: dict[str, Dataset], contract: DataContract,
             executed_at: str, run_id: str, input_fingerprint: str) -> ValidationResult:
    with localcontext(decimal_context()):
        return _validate(rule, datasets, contract, executed_at, run_id, input_fingerprint)


def _validate(rule: QualityRule, datasets: dict[str, Dataset], contract: DataContract,
              executed_at: str, run_id: str, input_fingerprint: str) -> ValidationResult:
    """Evaluate one declared rule. Missing/invalid evidence is never a passing assertion."""
    aware(executed_at)
    target = datasets.get(rule.target)
    rows = target.rows if target else None
    total = len(rows) if rows is not None else None
    exp = rule.expectation
    expected = exp.model_dump(mode="json")

    def result(passed, actual, failures, method, message, samples=None, metrics=None):
        status = "PASS" if passed is True else "UNKNOWN" if passed is None else "WARN" if rule.severity != "CRITICAL" else "FAIL"
        rate = str(Decimal(failures) / Decimal(total)) if failures is not None and total else None
        return ValidationResult(rule_id=rule.id, target_id=rule.target, status=status,
            expected=expected, actual=actual, failed_rows=failures, total_rows=total,
            failure_rate=rate, severity=rule.severity, blocking=rule.blocking,
            executed_at=executed_at, run_id=run_id, input_fingerprint=input_fingerprint,
            evidence=Evidence(method=method, message=message, sample_rows=samples or [], metrics=metrics or {}))

    def unknown(message):
        return result(None, None, None, exp.kind, message)

    if target is None:
        return unknown("Dataset evidence does not exist.")
    if target.id != rule.target:
        return unknown("Dataset identity does not match rule target.")

    if exp.kind == "schema":
        if rule.target != contract.dataset_id:
            return unknown("No designed schema contract exists for this target.")
        if target.columns is None:
            return unknown("Observed schema metadata is absent; row values do not establish a schema contract.")
        observed = {c.name: c for c in target.columns}
        structural = []
        for c in contract.columns:
            actual = observed.get(c.name)
            if actual is None:
                if c.required:
                    structural.append(f"Missing required column {c.name}")
                continue
            if actual.data_type != c.data_type:
                structural.append(f"{c.name}: expected {c.data_type}, observed {actual.data_type}")
            elif c.data_type == "DECIMAL" and (actual.precision, actual.scale) != (c.precision, c.scale):
                structural.append(f"{c.name}: decimal precision/scale differs")
            if not c.nullable and actual.nullable:
                structural.append(f"{c.name}: contract is NOT NULL, observed schema permits NULL")
        extra = sorted(set(observed) - {c.name for c in contract.columns})
        if extra and not exp.allow_extra_columns:
            structural.append(f"Extra columns forbidden: {', '.join(extra)}")
        bad = []
        if rows is not None:
            for i, row in enumerate(rows):
                if any((c.name not in row and c.required) or
                       (c.name in row and not value_matches(row[c.name], c)) for c in contract.columns):
                    bad.append(i)
        passed = False if structural or bad else None if rows is None else True
        return result(passed, {"structural_issues": structural, "invalid_rows": len(bad)},
                      len(bad) if rows is not None else None, "declared metadata + typed row validation",
                      "Schema and actual values match." if passed else "Inspect schema differences and invalid rows." if passed is False else "Row evidence is absent.",
                      _samples(rows, bad) if rows else [], {"extra_columns": extra})

    if rows is None:
        return unknown("Dataset rows are not available.")
    if exp.kind == "volume":
        passed = exp.minimum <= total <= exp.maximum
        return result(passed, {"rows": total}, 0 if passed else total, "inclusive authored row-count bounds",
                      f"{total} rows; expected {exp.minimum}–{exp.maximum}. This is a deterministic bound, not an anomaly model.")
    if exp.kind == "freshness":
        if target.loaded_at is None:
            return unknown("Data arrival timestamp is missing; task success is not freshness evidence.")
        try:
            delta = timestamp(executed_at) - timestamp(target.loaded_at)
            age = Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)
        except ValueError:
            return unknown("Arrival timestamp is invalid or lacks a timezone.")
        if age < 0:
            return unknown("Arrival timestamp lies in the future; clock evidence is inconsistent.")
        passed = age <= exp.maximum_age_minutes * 60
        return result(passed, {"age_minutes": str(age / 60), "loaded_at": target.loaded_at},
                      0 if passed else total, "explicit clock minus data arrival; inclusive maximum age",
                      f"Data age is {age / 60:g} minutes; allowed ≤ {exp.maximum_age_minutes} minutes.")
    if total == 0:
        return unknown("No rows to validate. An empty dataset does not prove row-level business validity; inspect volume.")

    needed = []
    if exp.kind == "unique":
        needed = exp.columns
    elif exp.kind in {"not_null", "accepted_values", "relationship", "reconciliation"}:
        needed = [exp.column]
    elif exp.kind == "business_rule":
        needed = {"completed_is_paid": ["status", "payment_status"],
                  "non_negative_revenue": ["net_revenue"],
                  "shipment_after_order": ["status", "ordered_at", "shipped_at"]}[exp.invariant]
    if any(key not in row for row in rows for key in needed):
        return unknown(f"At least one row lacks required evidence: {', '.join(needed)}. Run the schema check.")

    try:
        if exp.kind == "unique":
            keyed = [(i, [row[k] for k in exp.columns]) for i, row in enumerate(rows)]
            nulls = [i for i, values in keyed if any(v is None for v in values)]
            non_null = [(i, typed_key(values)) for i, values in keyed if i not in nulls]
            counts = Counter(key for _, key in non_null)
            affected = [i for i, key in non_null if counts[key] > 1]
            extras = sum(count - 1 for count in counts.values())
            failed = set(affected + (nulls if exp.null_policy == "fail" else []))
            if not non_null and exp.null_policy == "ignore":
                return unknown("All keys are NULL and ignored; no uniqueness evidence exists.")
            metrics = {"rows": total, "distinct_non_null_keys": len(counts), "duplicate_extra_rows": extras,
                       "duplicate_affected_rows": len(affected), "null_key_rows": len(nulls),
                       "declared_grain": contract.grain, "semantic_grain_proof": False}
            return result(not failed, metrics, len(failed), "count typed composite non-null keys; separate NULL policy",
                          f"{total} rows, {len(counts)} distinct non-null keys; {extras} extra repeated rows affect {len(affected)} rows. Key evidence supports the declared grain, not its semantic meaning.",
                          _samples(rows, failed), metrics)

        if exp.kind == "not_null":
            bad = [i for i, row in enumerate(rows) if row[exp.column] is None]
            complete = Decimal(total - len(bad)) / Decimal(total)
            numerator, denominator = exp.minimum_rate.as_integer_ratio()
            passed = (total - len(bad)) * denominator >= total * numerator
            return result(passed, {"not_null_rate": str(complete), "null_rows": len(bad)},
                          len(bad), "non-null rows / total rows; empty string, zero and false are non-null",
                          f"{total - len(bad)} / {total} rows have a value; minimum completeness is {exp.minimum_rate}.", _samples(rows, bad))

        if exp.kind == "accepted_values":
            accepted = {typed_key([v]) for v in exp.values}
            bad = [i for i, row in enumerate(rows) if
                   (row[exp.column] is None and not exp.allow_null) or
                   (row[exp.column] is not None and typed_key([row[exp.column]]) not in accepted)]
            return result(not bad, {"invalid_rows": len(bad), "allowed_values": exp.values}, len(bad),
                          "typed set membership + explicit NULL policy", f"{len(bad)} rows fall outside the allowed values.", _samples(rows, bad))

        if exp.kind == "relationship":
            parent = datasets.get(exp.parent_dataset)
            if parent is None or parent.rows is None:
                return unknown("Parent dataset evidence is missing; existence cannot be verified.")
            if any(exp.parent_column not in row for row in parent.rows):
                return unknown("Parent key column evidence is missing.")
            parent_keys = [typed_key([r[exp.parent_column]]) for r in parent.rows if r[exp.parent_column] is not None]
            duplicated = len(parent_keys) != len(set(parent_keys))
            keys = set(parent_keys)
            bad = [i for i, row in enumerate(rows) if
                   (row[exp.column] is None and not exp.allow_null) or
                   (row[exp.column] is not None and typed_key([row[exp.column]]) not in keys)]
            rate = Decimal(len(bad)) / Decimal(total)
            numerator, denominator = exp.maximum_orphan_rate.as_integer_ratio()
            passed = len(bad) * denominator <= total * numerator and not (exp.require_unique_parent and duplicated)
            return result(passed, {"unmatched_rows": len(bad), "matched_rows": total - len(bad),
                                  "duplicate_parent_key": duplicated}, len(bad), "typed FK membership; explicit NULL, orphan tolerance and parent uniqueness policies",
                          f"{len(bad)} orphan/disallowed NULL rows. Parent uniqueness {'fails' if duplicated else 'holds'}. Unknown members must exist as parent records; late dimensions require an explicit orphan tolerance.",
                          _samples(rows, bad))

        if exp.kind == "business_rule":
            bad = []
            for i, row in enumerate(rows):
                if exp.invariant == "completed_is_paid":
                    valid = row["status"] != "completed" or row["payment_status"] == "paid"
                elif exp.invariant == "non_negative_revenue":
                    valid = money(row["net_revenue"]) >= 0
                else:
                    shipped = row["shipped_at"]
                    valid = (row["status"] != "shipped") if shipped is None else timestamp(shipped) >= timestamp(row["ordered_at"])
                if not valid:
                    bad.append(i)
            return result(not bad, {"violations": len(bad)}, len(bad), exp.invariant,
                          f"{len(bad)} rows violate {exp.invariant.replace('_', ' ')}.", _samples(rows, bad))

        if exp.kind == "reconciliation":
            source, adjustment = datasets.get(exp.source_dataset), datasets.get(exp.adjustment_dataset)
            if source is None or adjustment is None or source.rows is None or adjustment.rows is None:
                return unknown("Reconciliation requires warehouse, captured-payment and refunded-return evidence.")
            if target.currency != exp.currency or source.currency != exp.currency or adjustment.currency != exp.currency:
                return unknown("Currencies are missing or different; totals cannot be compared safely.")
            for ds, column in [(target, exp.column), (source, exp.source_column), (adjustment, exp.adjustment_column)]:
                if any(column not in r or "currency" not in r or r["currency"] != exp.currency for r in ds.rows):
                    return unknown("Amount or row currency evidence is missing/mixed.")
            if any("status" not in r for r in source.rows + adjustment.rows):
                return unknown("Capture/refund status evidence is missing.")
            with localcontext() as ctx:
                ctx.prec = 80
                captured = sum((money(r[exp.source_column]) for r in source.rows if r["status"] == "captured"), Decimal(0))
                refunded = sum((money(r[exp.adjustment_column]) for r in adjustment.rows if r["status"] == "refunded"), Decimal(0))
                source_total = captured - refunded
                warehouse = sum((money(r[exp.column]) for r in rows), Decimal(0))
                difference = abs(source_total - warehouse)
                relative = difference / abs(source_total) if source_total else Decimal(0) if difference == 0 else None
                relative_pass = (source_total != 0 and Fraction(difference) <= Fraction(exp.relative_tolerance) * Fraction(source_total.copy_abs())) or difference == 0
                passed = difference <= exp.absolute_tolerance or relative_pass
            actual = {"captured_payments": str(captured), "refunded_returns": str(refunded),
                      "source_net_total": str(source_total), "warehouse_total": str(warehouse),
                      "absolute_difference": str(difference), "relative_difference": str(relative) if relative is not None else None,
                      "currency": exp.currency, "tolerance_policy": "absolute OR relative; inclusive; nonzero difference at zero source has no relative tolerance"}
            return result(passed, actual, 0 if passed else None, "SUM(captured payments) - SUM(refunded returns) ≈ SUM(net_revenue)",
                          f"Source net {source_total} {exp.currency}; warehouse {warehouse} {exp.currency}; absolute difference {difference}. Aggregate mismatch does not identify specific failing rows.", metrics=actual)
    except (ValueError, InvalidOperation, OverflowError) as exc:
        return unknown(f"Evidence cannot be evaluated: {exc}")
    return unknown("This expectation has no supported deterministic evaluator.")


def quality_gate(dataset_id: str, rules: list[QualityRule], results: list[ValidationResult],
                 run_id: str, input_fingerprint: str, executed_at: str) -> QualityGate:
    required = [r for r in rules if r.blocking]
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Gate rules must have unique IDs")
    if not rules or any(rule.target != dataset_id for rule in rules):
        raise ValueError("A gate requires rules that all target its dataset")
    blocked, reasons = [], []
    for rule in required:
        matches = [r for r in results if r.rule_id == rule.id]
        if len(matches) != 1:
            blocked.append(rule.id)
            reasons.append(f"{rule.name}: missing or duplicate validation evidence")
            continue
        r = matches[0]
        matches_context = (r.run_id == run_id and r.input_fingerprint == input_fingerprint and
                           r.executed_at == executed_at and r.target_id == rule.target and
                           r.severity == rule.severity and r.blocking == rule.blocking and
                           r.expected == rule.expectation.model_dump(mode="json"))
        if not matches_context or r.status != "PASS":
            blocked.append(rule.id)
            reasons.append(f"{rule.name}: {r.status if matches_context else 'stale or mismatched evidence'}")
    return QualityGate(dataset_id=dataset_id, status="BLOCKED" if blocked else "OPEN",
                       publication="WITHHELD" if blocked else "ELIGIBLE", blocking_rule_ids=blocked,
                       reasons=reasons, run_id=run_id, input_fingerprint=input_fingerprint)


def validate_bundle(request: ValidateRequest) -> ValidationBundle:
    rules = compile_contract(request.contract) + request.additional_rules
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Additional rule IDs must be unique and cannot replace contract rules")
    if any(r.target != request.contract.dataset_id for r in rules):
        raise ValueError("Every rule in this bundle must target the contracted dataset")
    if request.rule_ids is not None and (len(set(request.rule_ids)) != len(request.rule_ids) or set(request.rule_ids) - {r.id for r in rules}):
        raise ValueError("Selected rule IDs must exist and be unique")
    stamp = fingerprint(request, rules)
    selected = rules if request.rule_ids is None else [r for r in rules if r.id in request.rule_ids]
    results = [validate(r, request.datasets, request.contract, request.executed_at, request.run_id, stamp) for r in selected]
    gate = quality_gate(request.contract.dataset_id, rules, results, request.run_id, stamp, request.executed_at)
    events = [QualityEvent(dataset_id=r.target_id, rule_id=r.rule_id, status=r.status, severity=r.severity,
              expected=r.expected, actual=r.actual, failure_count=r.failed_rows, total_rows=r.total_rows,
              timestamp=r.executed_at, run_id=r.run_id, input_fingerprint=r.input_fingerprint, evidence=r.evidence) for r in results]
    summary = {status: sum(r.status == status for r in results) for status in ("PASS", "WARN", "FAIL", "UNKNOWN")}
    return ValidationBundle(contract=request.contract, rules=rules, results=results, gate=gate,
                            events=events, summary=summary, run_id=request.run_id, input_fingerprint=stamp)
