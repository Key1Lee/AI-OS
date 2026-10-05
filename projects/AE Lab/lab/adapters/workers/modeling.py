"""Consumer glue: project-owned inputs/oracles, unchanged native SQL evaluator."""
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
from data_modeling_lab.engine import ModelingEngine
from data_modeling_lab.contracts import BuildRequest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from lab.fixtures import key_batches, revenue

def main(payload):
    source = {o["order_id"]: o for o in payload["source"]}
    columns = {"order_id": "VARCHAR", "customer_id": "VARCHAR", "status": "VARCHAR",
               "order_amount": "DECIMAL(18,2)", "currency": "VARCHAR", "ordered_at": "TIMESTAMP WITH TIME ZONE"}
    raw_cols = {"orderId": "VARCHAR", "customerId": "VARCHAR", "status": "VARCHAR", "totalPriceCents": "BIGINT",
                "currency": "VARCHAR", "createdAt": "VARCHAR", "updatedAt": "VARCHAR", "sourceVersion": "INTEGER"}
    sql = "SELECT order_id, customer_id, status, order_amount, currency, ordered_at FROM loaded_orders WHERE status = 'completed'"
    outputs, results = [], []
    for batch in key_batches(payload["orders"]):
        expected = [source[k] for k in sorted({o["order_id"] for o in batch})]
        raw = [[o["order_id"], o["customer_id"], o["status"], int(Decimal(o["order_amount"]) * 100), o["currency"],
                o["ordered_at"], o["ordered_at"], 1] for o in expected]
        fixture = {"tables": {
            "raw_orders": {"columns": raw_cols, "rows": raw, "label": "Orders", "description": "Independent source reference",
                           "grain": "order_version", "grain_label": "one row per order version", "primary_key": ["orderId", "sourceVersion"]},
            "loaded_orders": {"columns": columns, "rows": [[o[c] for c in columns] for o in batch], "label": "Loaded orders",
                              "description": "Actual loader output; duplicates preserved", "grain": "order", "grain_label": "declared order grain", "primary_key": ["order_id"]},
            "customers": {"columns": {"customer_id": "VARCHAR"}, "rows": [[k] for k in sorted({o["customer_id"] for o in expected})],
                          "label": "Customers", "description": "Source customer keys", "grain": "customer", "grain_label": "customer", "primary_key": ["customer_id"]}}}
        oracle = {"columns": list(columns), "types": list(columns.values()), "rows": expected, "revenue": revenue(expected)}
        # DuckDB reports timezone-aware timestamp type as TIMESTAMP WITH TIME ZONE.
        engine = ModelingEngine(fixture, oracle)
        result = engine.build(BuildRequest(source_grain="order_version", grain="order", primary_key=["order_id"], sql=sql))
        exported = result.model_dump(mode="json")
        outputs.extend(exported["fact"]["rows"])
        exported["fact"]["rows"] = []
        exported["staging"]["rows"] = []
        for model in exported.get("inputs", []):
            model["rows"] = []
        # Keep native assertions, transformation SQL, schema, metric, and actual parents.
        results.append(exported)
    return {"status": "PASS" if results and all(r["evaluation"]["status"] == "pass" for r in results) else "FAIL",
            "rows": outputs, "row_count": len(outputs), "revenue": revenue(outputs), "sql": sql,
            "results": results, "provenance": "data_modeling_lab.ModelingEngine.build; complete key-co-located batches <=180"}

if __name__ == "__main__":
    print(json.dumps(main(json.load(sys.stdin))))
