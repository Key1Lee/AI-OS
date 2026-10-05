from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from importlib.resources import files
import json

from pydantic import Field, field_validator

from .contracts import (AcceptedValues, Business, Column, Contract, DataContract, Dataset,
                        Freshness, QualityRule, Reconciliation, Relationship, ValidateRequest,
                        Volume, aware)

SCENARIO_ID = "commerce-current-orders-v1"
BASE_CLOCK = "2026-10-02T00:00:00Z"  # 09:00 Asia/Seoul, independent of execution time.
BREAKS = {
    "duplicate": {"title": "Duplicate order 1007", "cause": "A source retry appended the same order twice.",
                  "expectation": "11 rows, 10 distinct order IDs", "consequence": "Order grain breaks. Summing the fixture's revenue rises from $550.00 to $620.00."},
    "orphan": {"title": "Use missing customer C999", "cause": "An order refers to a customer not in the parent dataset.",
               "expectation": "One orphan key", "consequence": "Customer joins can lose or misattribute this order. This is a possible consequence, not a measured downstream incident."},
    "schema": {"title": "Remove ordered_at", "cause": "A producer removed a required column.",
               "expectation": "Schema FAIL; dependent checks UNKNOWN", "consequence": "Time-based consumers cannot safely use this dataset."},
    "stale": {"title": "Advance the clock 3 hours", "cause": "No new data arrived while simulated time advanced.",
              "expectation": "Data age 210 minutes; limit 120", "consequence": "The dataset exists, but its arrival age exceeds the freshness promise."},
    "unpaid": {"title": "Complete an unpaid order", "cause": "Order 1007 is completed but payment_status is unpaid.",
               "expectation": "One business-rule violation", "consequence": "Completion no longer satisfies the documented payment assumption."},
    "null": {"title": "Erase order_id", "cause": "One required primary-key value is NULL.",
             "expectation": "Required value and key checks fail", "consequence": "A NULL key cannot identify an order."},
    "invalid": {"title": "Use status mystery", "cause": "A row contains a status outside the contract vocabulary.",
                "expectation": "Accepted-values FAIL", "consequence": "Consumers cannot interpret an undocumented status safely."},
    "warning": {"title": "Remove optional descriptions", "cause": "Two descriptions become NULL; required completeness is 90%.",
                "expectation": "80% completeness → WARN; publication eligible", "consequence": "This nonblocking documentation rule warns while critical checks still pass."},
    "shipment": {"title": "Ship before order time", "cause": "Order 1007 was shipped before it was ordered.",
                 "expectation": "One cross-field violation", "consequence": "The documented event-time relationship is contradicted."},
    "negative": {"title": "Set negative net revenue", "cause": "Order 1007 has net_revenue = -70.00.",
                 "expectation": "Nonnegative and reconciliation checks fail", "consequence": "This lab explicitly excludes negative net orders from its accepted business contract."},
    "reconcile": {"title": "Change warehouse revenue by $1", "cause": "One warehouse amount changed without a matching payment/refund.",
                  "expectation": "$1.00 absolute difference; tolerance $0.01", "consequence": "Key and null tests still pass, but Finance totals disagree."},
    "empty": {"title": "Lose every order", "cause": "The produced dataset is unexpectedly empty.",
              "expectation": "Volume FAIL; row checks UNKNOWN", "consequence": "An empty table does not establish valid business data."},
}


def fixture() -> dict[str, Dataset]:
    value = json.loads(files("quality_system").joinpath("fixtures/commerce.json").read_text())
    return {name: Dataset.model_validate(ds) for name, ds in value.items()}


def data_contract() -> DataContract:
    columns = fixture()["fct_orders"].columns
    def rule(id, name, description, dimension, expectation, **kwargs):
        return QualityRule(id=id, name=name, description=description, target="fct_orders",
                           dimension=dimension, expectation=expectation, **kwargs)
    rules = [
        rule("status_allowed", "Status has an agreed meaning", "Only documented order statuses may be consumed.",
             "validity", AcceptedValues(column="status", values=["pending", "completed", "cancelled", "shipped"])),
        rule("completed_paid", "Completed orders are paid", "The producer promises that completed orders have a paid payment_status.",
             "business_rule", Business(invariant="completed_is_paid")),
        rule("nonnegative", "Net revenue is nonnegative", "This scenario's net-order definition excludes negative amounts. Other business contracts may allow them.",
             "business_rule", Business(invariant="non_negative_revenue")),
        rule("shipment_order", "Shipment follows order time", "A shipped order must have a shipment timestamp at or after ordered_at.",
             "consistency", Business(invariant="shipment_after_order")),
        rule("freshness", "Data arrived within 2 hours", "Freshness measures data arrival age; a successful task alone cannot prove this.",
             "freshness", Freshness(maximum_age_minutes=120)),
        rule("volume", "The exercise contains 10–12 orders", "These explicit fixture bounds detect missing output, not statistical anomalies.",
             "volume", Volume(minimum=10, maximum=12)),
        rule("reconciliation", "Net revenue reconciles", "Captured payments minus refunded returns must reconcile to net USD revenue within absolute OR relative tolerance.",
             "reconciliation", Reconciliation()),
        rule("description_complete", "Descriptions are at least 90% complete", "Optional descriptions improve readability; their threshold is nonblocking.",
             "completeness", {"kind": "not_null", "column": "description", "minimum_rate": "0.90"},
             severity="WARNING", blocking=False),
    ]
    return DataContract(id="current_orders_net_usd", dataset_id="fct_orders", grain="1 row / current order",
                        primary_key=["order_id"], columns=columns,
                        relationships=[Relationship(column="customer_id", parent_dataset="customers", parent_column="customer_id")],
                        rules=rules, owner="Commerce Analytics", currency="USD",
                        semantic_meaning="One current record for each order. Net revenue is captured USD payments less refunded USD returns allocated to that order. The fixture contains 10 completed paid orders; no conversion, tax or chargeback logic is implied. This differs from Modeling's gross completed-order Revenue metric.")


class ScenarioRequest(Contract):
    corruptions: list[str] = Field(default_factory=list, max_length=12)
    executed_at: str = BASE_CLOCK
    run_id: str = Field(default="commerce-run-1", min_length=1, max_length=100)
    additional_rules: list[QualityRule] = Field(default_factory=list, max_length=10)
    rule_ids: list[str] | None = Field(default=None, max_length=80)

    _aware = field_validator("executed_at")(aware)

    @field_validator("corruptions")
    @classmethod
    def known_breaks(cls, values):
        if len(values) != len(set(values)) or set(values) - set(BREAKS):
            raise ValueError("Corruptions must be distinct known scenario changes")
        return values


def scenario_input(request: ScenarioRequest) -> ValidateRequest:
    from .engine import timestamp
    datasets = fixture()
    target = datasets["fct_orders"]
    row = target.rows[6]
    executed_at = request.executed_at
    for corruption in request.corruptions:
        if corruption == "duplicate":
            target.rows.append(deepcopy(row))
        elif corruption == "orphan":
            row["customer_id"] = "C999"
        elif corruption == "schema":
            target.columns = [c for c in target.columns if c.name != "ordered_at"]
            for item in target.rows:
                item.pop("ordered_at", None)
        elif corruption == "stale":
            executed_at = (timestamp(executed_at) + timedelta(hours=3)).isoformat()
        elif corruption == "unpaid":
            row["payment_status"] = "unpaid"
        elif corruption == "null":
            row["order_id"] = None
        elif corruption == "invalid":
            row["status"] = "mystery"
        elif corruption == "warning":
            target.rows[0]["description"] = None
            target.rows[1]["description"] = None
        elif corruption == "shipment":
            row["shipped_at"] = "2026-09-27T00:00:00Z"
        elif corruption == "negative":
            row["net_revenue"] = "-70.00"
        elif corruption == "reconcile":
            row["net_revenue"] = "71.00"
        elif corruption == "empty":
            target.rows.clear()
    return ValidateRequest(contract=data_contract(), datasets=datasets, executed_at=executed_at,
                           run_id=request.run_id, additional_rules=request.additional_rules, rule_ids=request.rule_ids)


def scenario_definition():
    from .engine import compile_contract
    contract = data_contract()
    return {"contract_version": "quality-scenario-v1", "id": SCENARIO_ID,
            "title": "A table exists. Can we trust it?", "clock": BASE_CLOCK, "timezone": "Asia/Seoul",
            "contract": contract.model_dump(mode="json"),
            "rules": [r.model_dump(mode="json") for r in compile_contract(contract)],
            "datasets": {k: ds.model_dump(mode="json") for k, ds in fixture().items()},
            "corruptions": BREAKS,
            "flow": ["raw_orders", "stg_orders", "int_orders", "fct_orders", "mart_revenue"],
            "flow_note": "Authored teaching stages. Only fct_orders is validated in this slice; upstream stages are context, not independently certified.",
            "learning_levels": ["Nulls, unique keys, valid values", "Relationships, grain, schema",
                                "Business rules and reconciliation", "Freshness, volume and gates",
                                "Contracts and evolution", "Cross-system quality", "Senior diagnostic practice"]}
