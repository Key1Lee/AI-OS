"""Standalone worker. Keep imports independent of application state and secrets."""
from __future__ import annotations

import datetime as dt
import decimal
import json
import math
import resource
import sys

import duckdb


def encode(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite result values are unsupported")
    if not isinstance(value, (str, int, float, bool, type(None))):
        raise ValueError("Return scalar columns rather than nested values")
    if isinstance(value, str) and len(value) > 64000:
        raise ValueError("A result cell exceeds the output limit")
    return value


def main():
    payload = json.load(sys.stdin)
    resource.setrlimit(resource.RLIMIT_CPU, (payload["cpu_seconds"], payload["cpu_seconds"]))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    con = duckdb.connect(":memory:", config={
        "enable_external_access": "false",
        "autoload_known_extensions": "false",
        "autoinstall_known_extensions": "false",
        "allow_community_extensions": "false",
        "allow_unsigned_extensions": "false",
        "memory_limit": "128MB",
        "threads": "1",
        "max_temp_directory_size": "0B",
    })
    try:
        for table in payload["tables"]:
            columns = ",".join(f'"{c["name"]}" {c["type"]}' for c in table["columns"])
            con.execute(f'CREATE TABLE "{table["name"]}" ({columns})')
            if table["rows"]:
                placeholders = ",".join("?" for _ in table["columns"])
                con.executemany(f'INSERT INTO "{table["name"]}" VALUES ({placeholders})', table["rows"])
        con.execute("SET lock_configuration = true")
        statements = con.extract_statements(payload["code"])
        if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
            return {"ok": False, "kind": "policy", "error": "Use one SELECT query (WITH is allowed). Data or configuration changes are disabled."}
        cursor = con.execute(payload["code"])
        columns = [str(col[0]) for col in cursor.description]
        types = [str(col[1]) for col in cursor.description]
        rows = cursor.fetchmany(payload["max_rows"] + 1)
        if len(rows) > payload["max_rows"]:
            return {"ok": False, "kind": "limit", "error": "Query output exceeds the 1,000-row limit. Check the required grain."}
        result = {"ok": True, "columns": columns, "types": types, "rows": [[encode(v) for v in row] for row in rows]}
        if len(json.dumps(result)) > 2000000:
            return {"ok": False, "kind": "limit", "error": "Query output exceeds the response limit."}
        return result
    except (duckdb.Error, ValueError) as exc:
        return {"ok": False, "kind": "runtime", "error": str(exc)[:1200]}
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(main(), allow_nan=False))
