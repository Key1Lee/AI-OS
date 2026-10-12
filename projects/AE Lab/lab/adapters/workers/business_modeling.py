"""Generic fixture/query use of the native Modeling connection and key assertions.

The commerce-specific BuildRequest evaluator is intentionally not presented as
certifying unrelated business grains. The Lab supplies its independent oracles.
"""
import json
import sys
sys.dont_write_bytecode = True
from data_modeling_lab.engine import ModelingEngine

def execute(payload):
    tables = payload["tables"]
    # Native connection also prepares its standard commerce staging view. Empty
    # compatibility input prevents that view from contributing business rows.
    tables["raw_orders"] = {"columns": {"orderId":"VARCHAR","customerId":"VARCHAR","status":"VARCHAR",
        "totalPriceCents":"BIGINT","currency":"VARCHAR","createdAt":"VARCHAR","updatedAt":"VARCHAR","sourceVersion":"INTEGER"}, "rows": []}
    engine = ModelingEngine({"tables":tables}, {})
    with engine.connection() as db:
        db.execute("CREATE TEMP TABLE business_output AS " + payload["sql"])
        rows = engine.rows(db, "business_output")
        tests = [test.model_dump(mode="json") for test in engine.key_tests(db, "business_output", ["entity_id"])]
        quarantine = []
        if payload.get("quarantine_sql"):
            db.execute("CREATE TEMP TABLE quarantine AS " + payload["quarantine_sql"])
            quarantine = engine.rows(db, "quarantine")
        return {"rows": rows, "tests": tests, "quarantine":quarantine,
                "columns":[column.model_dump(mode="json") for column in engine.columns(db,"business_output")],
                "provenance":"data_modeling_lab.ModelingEngine.connection / rows / key_tests; authored business SELECT"}

if __name__ == "__main__":
    print(json.dumps(execute(json.load(sys.stdin)), allow_nan=False))
