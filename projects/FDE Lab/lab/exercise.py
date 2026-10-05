"""A bounded SQL repair exercise, with an oracle independent of learner SQL.

The public text is released by the lab's discovery gates. The expected report
is calculated from Python rows. A broken regression branch is introduced only
after the learner's first repair has passed its baseline tests.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import hashlib
import json
import random
import sqlite3
import time


Order = tuple[str, str, int, str, int, str]
Refund = tuple[str, str, int, int]
Promotion = tuple[str, str]

SCHEMA = """CREATE TABLE raw_orders (
    event_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);
CREATE TABLE raw_refunds (
    event_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL
);
CREATE TABLE promotions (
    order_id TEXT NOT NULL,
    promo_code TEXT NOT NULL
);"""


@dataclass(frozen=True)
class _Fixture:
    name: str
    orders: tuple[Order, ...]
    refunds: tuple[Refund, ...]
    promotions: tuple[Promotion, ...]


_BASELINE = _Fixture(
    "UTC daily net revenue contract",
    orders=(
        ("oe100v1", "o100", 1, "pending", 12000, "2026-09-29T23:40:00Z"),
        ("oe100v2", "o100", 2, "completed", 12000, "2026-09-29T23:40:00Z"),
        ("oe101v1", "o101", 1, "completed", 8500, "2026-09-29T09:15:00Z"),
        ("oe101v2", "o101", 2, "cancelled", 8500, "2026-09-29T09:15:00Z"),
        ("oe102v1", "o102", 1, "completed", 5000, "2026-09-29T18:20:00Z"),
        ("oe200v1", "o200", 1, "completed", 20000, "2026-09-30T00:20:00Z"),
        ("oe200v2", "o200", 2, "completed", 18000, "2026-09-30T00:20:00Z"),
        ("oe201v1", "o201", 1, "completed", 7000, "2026-09-30T16:10:00Z"),
        ("oe202v1", "o202", 1, "pending", 9000, "2026-09-30T20:00:00Z"),
    ),
    refunds=(
        ("r100a", "o100", 1, 1000),
        ("r100a", "o100", 2, 1500),
        ("r100b", "o100", 1, 500),
        ("r102", "o102", 1, 1000),
        ("r200", "o200", 1, 2000),
        ("r201", "o201", 1, 7000),
        ("r101", "o101", 1, 1000),
    ),
    promotions=(
        ("o100", "WELCOME"),
        ("o100", "AUTUMN"),
        ("o101", "WELCOME"),
        ("o200", "VIP"),
        ("o200", "AUTUMN"),
        ("o200", "APP"),
        ("o201", "VIP"),
        ("o202", "WELCOME"),
    ),
)


def starter() -> str:
    """Return the analyst's broken model, never a reference repair."""
    return """-- Analyst model under investigation: daily revenue in cents.
SELECT date(o.occurred_at) AS report_date,
       SUM(o.amount_cents - COALESCE(r.amount_cents, 0)) AS net_revenue_cents
FROM raw_orders AS o
LEFT JOIN raw_refunds AS r ON r.order_id = o.order_id
LEFT JOIN promotions AS p ON p.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY date(o.occurred_at)
ORDER BY report_date;
"""


def incident_starter() -> str:
    """A post-prototype regression: correct with unique deliveries, replay-unsafe.

    Equal versions survive the branch's tie handling. This deliberately makes
    the injected incident reproducible, without overwriting the learner's model.
    """
    return """-- Candidate optimization branch introduced during the simulated incident.
WITH order_candidates AS (
    SELECT *, RANK() OVER (PARTITION BY order_id ORDER BY version DESC) AS choice
    FROM raw_orders
), refund_candidates AS (
    SELECT *, RANK() OVER (PARTITION BY event_id ORDER BY version DESC) AS choice
    FROM raw_refunds
), refunds_by_order AS (
    SELECT order_id, SUM(amount_cents) AS refunded_cents
    FROM refund_candidates
    WHERE choice = 1
    GROUP BY order_id
)
SELECT date(o.occurred_at) AS report_date,
       SUM(o.amount_cents - COALESCE(r.refunded_cents, 0)) AS net_revenue_cents
FROM order_candidates AS o
LEFT JOIN refunds_by_order AS r ON r.order_id = o.order_id
WHERE o.choice = 1 AND o.status = 'completed'
GROUP BY date(o.occurred_at)
ORDER BY report_date;
"""


def task() -> str:
    """The discovered finance contract, with no implementation hints."""
    return """Repair the SQL model against the discovered finance contract.

Return exactly report_date (YYYY-MM-DD) and net_revenue_cents (INTEGER), one
row per UTC date that has at least one eligible completed order. Include a
date even when its completed orders have zero net revenue.

A logical order is identified by order_id. Its greatest version is its
current state; versions can revise status, amount, and occurred_at. Count
only orders whose current status is completed. Attribute their revenue to
the UTC date of their current occurred_at. All timestamps in these tables
use UTC ISO 8601 with a Z suffix.

A logical refund is identified by refund event_id. Use its greatest version,
subtract its amount once from its associated eligible order, and attribute
it to that order's report date. Different refund event_ids can have equal
amounts. A refund attached to an ineligible order does not count.

Delivery can repeat an identical event row, including event_id and version.
Conflicting payloads for the same identity/version are outside this exercise.
Promotions are optional descriptive rows: an order can have none or many.
Neither promotion multiplicity nor delivery order may change revenue.

Use one read-only SELECT statement (WITH clauses are supported), using only
the three fixture tables. The checker varies amounts, versions, statuses,
dates, refunds, and promotion counts; a hardcoded report is not a repair.
The incident check also replays deliveries into both raw event tables.
"""


def _literal(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def public_fixture() -> str:
    """Return reproducible DDL and baseline rows, without a solution query."""
    sections = ["-- Northstar exercise fixture: all amounts are integer cents.", SCHEMA]
    for table, rows in (
        ("raw_orders", _BASELINE.orders),
        ("raw_refunds", _BASELINE.refunds),
        ("promotions", _BASELINE.promotions),
    ):
        values = ",\n".join("(" + ", ".join(map(_literal, row)) + ")" for row in rows)
        sections.append(f"INSERT INTO {table} VALUES\n{values};")
    return "\n\n".join(sections) + "\n"


def _expected(fixture: _Fixture) -> list[tuple[str, int]]:
    """Calculate the contract with Python identity maps, not reference SQL."""
    latest_orders: dict[str, Order] = {}
    for row in fixture.orders:
        existing = latest_orders.get(row[1])
        if existing is None or row[2] > existing[2]:
            latest_orders[row[1]] = row
    latest_refunds: dict[str, Refund] = {}
    for row in fixture.refunds:
        existing = latest_refunds.get(row[0])
        if existing is None or row[2] > existing[2]:
            latest_refunds[row[0]] = row
    refunds_by_order: dict[str, int] = {}
    for row in latest_refunds.values():
        refunds_by_order[row[1]] = refunds_by_order.get(row[1], 0) + row[3]
    report: dict[str, int] = {}
    for order in latest_orders.values():
        if order[3] == "completed":
            day = order[5][:10]
            report[day] = report.get(day, 0) + order[4] - refunds_by_order.get(order[1], 0)
    return sorted(report.items())


def _shuffled(fixture: _Fixture, seed: int, name: str) -> _Fixture:
    rng = random.Random(seed)
    groups = []
    for rows in (fixture.orders, fixture.refunds, fixture.promotions):
        copy = list(rows)
        rng.shuffle(copy)
        groups.append(tuple(copy))
    return _Fixture(name, *groups)


def _fixtures(incident: bool) -> tuple[_Fixture, ...]:
    """Independent deterministic counterexamples to common broken repairs."""
    changed_amounts = replace(
        _BASELINE,
        name="current order amounts and integer cents",
        orders=tuple(
            (*row[:4], row[4] + 137, row[5]) if row[1] == "o200" and row[2] == 2 else row
            for row in _BASELINE.orders
        ),
    )
    changed_status = replace(
        _BASELINE,
        name="latest order status before eligibility",
        orders=_BASELINE.orders + (
            ("oe102v2", "o102", 2, "cancelled", 5000, "2026-09-29T18:20:00Z"),
            ("oe202v2", "o202", 2, "completed", 9000, "2026-09-30T20:00:00Z"),
            ("oe101v3", "o101", 3, "completed", 8100, "2026-09-29T09:15:00Z"),
        ),
    )
    changed_refunds = replace(
        _BASELINE,
        name="latest refund version and distinct refund identities",
        refunds=_BASELINE.refunds + (
            ("r100a", "o100", 3, 1700),
            ("r100c", "o100", 1, 500),
            ("r200", "o200", 2, 2201),
        ),
    )
    changed_promotions = replace(
        _BASELINE,
        name="promotion fanout and orders without promotions",
        promotions=_BASELINE.promotions + (
            ("o100", "EXTRA"), ("o200", "EXTRA"), ("o102", "FIRST"),
        ),
    )
    changed_dates = replace(
        _BASELINE,
        name="latest order timestamp and UTC date attribution",
        orders=_BASELINE.orders + (
            ("oe100v3", "o100", 3, "completed", 12000, "2026-09-30T00:05:00Z"),
            ("oe300v1", "o300", 1, "completed", 3301, "2026-10-01T00:00:00Z"),
        ),
        refunds=_BASELINE.refunds + (("r300", "o300", 1, 301),),
    )
    zero_date = replace(
        _BASELINE,
        name="zero net revenue dates remain present",
        orders=_BASELINE.orders + (
            ("oe400v1", "o400", 1, "completed", 7000, "2026-10-02T11:00:00Z"),
        ),
        refunds=_BASELINE.refunds + (("r400", "o400", 1, 7000),),
    )
    fixtures = [
        _BASELINE,
        changed_amounts,
        changed_status,
        changed_refunds,
        changed_promotions,
        changed_dates,
        zero_date,
        _shuffled(changed_refunds, 406, "delivery order independence"),
    ]
    if incident:
        # Replay old and current payloads; both orders and refunds are affected.
        for index, fixture in enumerate(tuple(fixtures)):
            replay = replace(
                fixture,
                orders=fixture.orders + fixture.orders + fixture.orders[::2],
                refunds=fixture.refunds + fixture.refunds + fixture.refunds[::2],
            )
            fixtures.append(_shuffled(replay, 900 + index, f"delivery replay invariance: {fixture.name}"))
    return tuple(fixtures)


_MAX_SQL_BYTES = 32_768
_MAX_RESULT_ROWS = 64
_MAX_PROGRESS_CALLS = 1000
_MAX_QUERY_SECONDS = 0.5
_TABLES = frozenset({"raw_orders", "raw_refunds", "promotions"})
_SAFE_FUNCTIONS = frozenset({
    "abs", "avg", "coalesce", "count", "date", "datetime", "dense_rank",
    "first_value", "ifnull", "instr", "julianday", "last_value", "length",
    "lower", "ltrim", "max", "min", "nullif", "nth_value", "printf", "rank",
    "replace", "round", "row_number", "rtrim", "strftime", "substr", "substring",
    "sum", "time", "total", "trim", "typeof", "unicode", "unixepoch", "upper",
})


class _QueryFailure(Exception):
    """A learner-facing failure, already stripped of implementation details."""


def _run(sql: str, fixture: _Fixture) -> list[tuple[str, int]]:
    connection = sqlite3.connect(":memory:")
    denied: list[str] = []
    progress_calls = 0
    interrupted = False
    started = time.monotonic()

    def authorize(action: int, arg1: str | None, arg2: str | None,
                  database: str | None, source: str | None) -> int:
        if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE}:
            return sqlite3.SQLITE_OK
        # SQLite supplies database=None for a table scan that reads no columns,
        # such as SELECT 1 FROM raw_orders; the allowed table set is still fixed.
        if action == sqlite3.SQLITE_READ and database in {None, "main"} and arg1 in _TABLES:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in _SAFE_FUNCTIONS:
            return sqlite3.SQLITE_OK
        denied.append("Only bounded reads of the three fixture tables and safe SQL functions are allowed.")
        return sqlite3.SQLITE_DENY

    def bound_execution() -> int:
        nonlocal progress_calls, interrupted
        progress_calls += 1
        interrupted = (
            progress_calls >= _MAX_PROGRESS_CALLS
            or time.monotonic() - started > _MAX_QUERY_SECONDS
        )
        return int(interrupted)

    try:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO raw_orders VALUES (?, ?, ?, ?, ?, ?)", fixture.orders)
        connection.executemany("INSERT INTO raw_refunds VALUES (?, ?, ?, ?)", fixture.refunds)
        connection.executemany("INSERT INTO promotions VALUES (?, ?)", fixture.promotions)
        connection.commit()
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        # Length limits also bound work inside a single string function, which
        # the VM progress callback cannot interrupt until that function returns.
        if not hasattr(connection, "setlimit"):
            raise _QueryFailure("The SQL exercise requires Python 3.11 or newer for bounded execution.")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 131_072)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, _MAX_SQL_BYTES)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 16)
        connection.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 32)
        connection.set_authorizer(authorize)
        started = time.monotonic()
        connection.set_progress_handler(bound_execution, 1000)
        cursor = connection.execute(sql)
        columns = [column[0] for column in cursor.description or ()]
        if columns != ["report_date", "net_revenue_cents"]:
            raise _QueryFailure("Return exactly report_date and net_revenue_cents, in that order.")
        rows = cursor.fetchmany(_MAX_RESULT_ROWS + 1)
        if len(rows) > _MAX_RESULT_ROWS:
            raise _QueryFailure(f"Output exceeds the {_MAX_RESULT_ROWS}-row exercise bound.")
        seen_dates: set[str] = set()
        report: list[tuple[str, int]] = []
        for day, cents in rows:
            if not isinstance(day, str) or len(day) != 10:
                raise _QueryFailure("report_date must be a YYYY-MM-DD date string.")
            try:
                valid_day = date.fromisoformat(day)
            except ValueError as error:
                raise _QueryFailure("report_date must be a valid YYYY-MM-DD date string.") from error
            if valid_day.isoformat() != day:
                raise _QueryFailure("report_date must use YYYY-MM-DD formatting.")
            if day in seen_dates:
                raise _QueryFailure("Return one row per report_date; duplicate dates were found.")
            if not isinstance(cents, int):
                raise _QueryFailure("net_revenue_cents must be an INTEGER, with no null or fractional cents.")
            seen_dates.add(day)
            report.append((day, cents))
        return sorted(report)
    except sqlite3.Error as error:
        if denied:
            raise _QueryFailure(denied[0]) from error
        if interrupted:
            raise _QueryFailure("Query exceeded the bounded execution budget; check its termination and joins.") from error
        raise _QueryFailure(f"SQL could not run: {error}") from error
    finally:
        connection.close()


def check(sql: str, incident: bool = False) -> dict:
    """Execute a repair against independent mutations and optional replays.

    Failure details identify the violated contract and actual output without
    disclosing a repair. Every connection is fresh, memory-only, and read-only.
    The hash lets the engine tie validation to the exact submitted artifact.
    """
    artifact_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    checks: list[dict] = []
    if not sql.strip() or len(sql.encode("utf-8")) > _MAX_SQL_BYTES:
        checks.append({
            "name": "query safety and bounded execution",
            "passed": False,
            "detail": f"Submit a nonempty SQL statement no larger than {_MAX_SQL_BYTES} UTF-8 bytes.",
        })
        return {"passed": False, "checks": checks, "artifact_hash": artifact_hash}
    for fixture in _fixtures(incident):
        try:
            actual = _run(sql, fixture)
        except _QueryFailure as error:
            checks.append({"name": "query safety, execution, and output contract", "passed": False, "detail": str(error)})
            break
        passed = actual == _expected(fixture)
        detail = "Matched the independent fixture oracle."
        if not passed:
            detail = "The report violates this contract under a deterministic fixture variation. Actual rows: " + json.dumps(actual)
        checks.append({"name": fixture.name, "passed": passed, "detail": detail})
    return {"passed": bool(checks) and all(item["passed"] for item in checks), "checks": checks, "artifact_hash": artifact_hash}
