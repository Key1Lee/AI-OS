from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

FIELDS = ("order_id", "customer_id", "status", "order_amount", "currency", "ordered_at")
DDL = "(order_id TEXT NOT NULL,customer_id TEXT NOT NULL,status TEXT NOT NULL,amount_cents INTEGER NOT NULL,currency TEXT NOT NULL,ordered_at TEXT NOT NULL)"

class Warehouse:
    def __init__(self, path: Path):
        self.path = path
        with self.connect() as db:
            db.execute(f"CREATE TABLE IF NOT EXISTS orders_raw {DDL}")
            db.execute(f"CREATE TABLE IF NOT EXISTS fct_orders {DDL}")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    @staticmethod
    def values(orders):
        return [(o["order_id"], o["customer_id"], o["status"], int(Decimal(o["order_amount"]) * 100),
                 o["currency"], o["ordered_at"]) for o in orders]

    def enable_upsert(self):
        """Repair historical duplicates and enforce the declared key atomically."""
        with self.connect() as db:
            db.execute("DELETE FROM orders_raw WHERE rowid NOT IN (SELECT max(rowid) FROM orders_raw GROUP BY order_id)")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS orders_order_id ON orders_raw(order_id)")

    def write(self, orders: list[dict], policy: str):
        if policy not in {"append", "upsert"}:
            raise ValueError("Unknown load policy")
        sql = "INSERT INTO orders_raw VALUES (?,?,?,?,?,?)"
        if policy == "upsert":
            sql += " ON CONFLICT(order_id) DO UPDATE SET customer_id=excluded.customer_id,status=excluded.status,amount_cents=excluded.amount_cents,currency=excluded.currency,ordered_at=excluded.ordered_at"
        with self.connect() as db:
            db.executemany(sql, self.values(orders))

    def materialize(self, orders: list[dict]):
        with self.connect() as db:
            db.execute("DELETE FROM fct_orders")
            db.executemany("INSERT INTO fct_orders VALUES (?,?,?,?,?,?)", self.values(orders))

    def rows(self, table: str = "orders_raw") -> list[dict]:
        if table not in {"orders_raw", "fct_orders"}:
            raise ValueError("Unknown lab table")
        with self.connect() as db:
            rows = db.execute(f"SELECT * FROM {table} ORDER BY order_id, rowid").fetchall()
        return [dict(zip(FIELDS, [r[0], r[1], r[2], f"{Decimal(r[3]) / 100:.2f}", r[4], r[5]])) for r in rows]

    def has_key(self) -> bool:
        with self.connect() as db:
            return any(r[1] == "orders_order_id" and r[2] == 1 for r in db.execute("PRAGMA index_list(orders_raw)"))
