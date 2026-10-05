from __future__ import annotations

import json
from importlib.resources import files

import duckdb


def fixture_data() -> dict:
    return json.loads(files("modeling_fixtures.ecommerce").joinpath("fixture.json").read_text())


def expected_data() -> dict:
    return json.loads(files("modeling_fixtures.ecommerce").joinpath("expected.json").read_text())


def load_fixtures(db: duckdb.DuckDBPyConnection, fixture: dict | None = None) -> None:
    fixture = fixture or fixture_data()
    # Fixture schemas are project-owned, never supplied by an API request.
    for name, definition in fixture["tables"].items():
        cols = ", ".join(f'"{col}" {dtype}' for col, dtype in definition["columns"].items())
        db.execute(f'CREATE TABLE "{name}" ({cols})')
        placeholders = ",".join("?" for _ in definition["columns"])
        if definition["rows"]:
            db.executemany(f'INSERT INTO "{name}" VALUES ({placeholders})', definition["rows"])
    # Use the same timestamp semantics as staging; equal instants can have different offsets.
    ties = db.execute("""SELECT count(*) FROM (
        SELECT orderId, CAST(updatedAt AS TIMESTAMPTZ), sourceVersion
        FROM raw_orders GROUP BY ALL HAVING count(*) > 1
    )""").fetchone()[0]
    repeated_keys = db.execute("""SELECT count(*) FROM (
        SELECT orderId, sourceVersion FROM raw_orders GROUP BY ALL HAVING count(*) > 1
    )""").fetchone()[0]
    null_keys = db.execute("SELECT count(*) FROM raw_orders WHERE orderId IS NULL OR updatedAt IS NULL OR sourceVersion IS NULL").fetchone()[0]
    if ties or repeated_keys or null_keys:
        raise ValueError("Ambiguous source versions: non-null source keys and updatedAt/sourceVersion must resolve deduplication ties.")
