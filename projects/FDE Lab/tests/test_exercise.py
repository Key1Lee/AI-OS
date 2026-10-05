import hashlib
import sqlite3
import time
import unittest

from lab import exercise


# A correct repair lives in tests, never in the learner's starter or task.
CORRECT_SQL = """
WITH order_candidates AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY version DESC) AS choice
    FROM raw_orders
), refund_candidates AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY version DESC) AS choice
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


class ExerciseTests(unittest.TestCase):
    def test_broken_starter_fails_without_reference_solution(self):
        result = exercise.check(exercise.starter())
        self.assertFalse(result["passed"])
        self.assertTrue(any(not item["passed"] for item in result["checks"]))
        self.assertNotIn("ROW_NUMBER", exercise.starter())
        self.assertNotIn("order_candidates", str(result))

    def test_correct_repair_passes_mutations_and_replays(self):
        base = exercise.check(CORRECT_SQL)
        replay = exercise.check(CORRECT_SQL, incident=True)
        self.assertTrue(base["passed"], base)
        self.assertTrue(replay["passed"], replay)
        self.assertEqual(len(base["checks"]), 8)
        self.assertEqual(len(replay["checks"]), 16)
        self.assertEqual(base["artifact_hash"], hashlib.sha256(CORRECT_SQL.encode()).hexdigest())
        self.assertEqual(base["artifact_hash"], replay["artifact_hash"])

    def test_incident_branch_reproduces_replay_only_regression(self):
        sql = exercise.incident_starter()
        self.assertTrue(exercise.check(sql)["passed"])
        incident = exercise.check(sql, incident=True)
        self.assertFalse(incident["passed"])
        self.assertTrue(all(item["passed"] for item in incident["checks"][:8]))
        self.assertTrue(any(not item["passed"] for item in incident["checks"][8:]))

    def test_baseline_fixture_is_reproducible_and_matches_scenario(self):
        fixture = exercise.public_fixture()
        with sqlite3.connect(":memory:") as connection:
            connection.executescript(fixture)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM raw_orders").fetchone()[0], 9)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM raw_refunds").fetchone()[0], 7)
            self.assertEqual(connection.execute(CORRECT_SQL).fetchall(), [
                ("2026-09-29", 14000), ("2026-09-30", 16000),
            ])
        self.assertEqual(fixture, exercise.public_fixture())
        self.assertNotIn("WITH order_candidates", fixture)

    def test_hardcoded_baseline_is_rejected(self):
        sql = """SELECT '2026-09-29' AS report_date, 14000 AS net_revenue_cents
                 UNION ALL SELECT '2026-09-30', 16000"""
        result = exercise.check(sql)
        self.assertTrue(result["checks"][0]["passed"])
        self.assertFalse(result["passed"])
        self.assertTrue(any(not item["passed"] for item in result["checks"][1:]))

    def test_authorizer_rejects_writes_files_pragmas_and_unsafe_functions(self):
        for sql in (
            "DELETE FROM raw_orders",
            "DROP TABLE raw_orders",
            "CREATE TABLE stolen AS SELECT * FROM raw_orders",
            "ATTACH DATABASE '/tmp/fde-must-not-create.db' AS stolen",
            "PRAGMA table_info(raw_orders)",
            "SELECT load_extension('/tmp/extension')",
            "SELECT name FROM sqlite_master",
            "WITH x AS (SELECT 1) UPDATE raw_orders SET amount_cents = 0",
        ):
            with self.subTest(sql=sql):
                result = exercise.check(sql)
                self.assertFalse(result["passed"], sql)
                self.assertIn("Only bounded reads", result["checks"][0]["detail"])
        self.assertTrue(exercise.check(CORRECT_SQL)["passed"])

    def test_runaway_recursive_query_is_cancelled(self):
        sql = """WITH RECURSIVE spins(n) AS (
                    SELECT 1 UNION ALL SELECT n + 1 FROM spins
                 )
                 SELECT '2026-09-29' AS report_date, SUM(n) AS net_revenue_cents
                 FROM spins"""
        started = time.monotonic()
        result = exercise.check(sql)
        self.assertFalse(result["passed"])
        self.assertIn("bounded execution budget", result["checks"][0]["detail"])
        self.assertLess(time.monotonic() - started, 2.0)

    def test_invalid_result_shapes_and_unbounded_output_are_rejected(self):
        for sql, expected in (
            ("SELECT '2026-09-29' AS day, 14000 AS cents", "Return exactly"),
            ("SELECT '2026-09-29' AS report_date, 14000.5 AS net_revenue_cents", "INTEGER"),
            ("SELECT '2026-09-29' AS report_date, NULL AS net_revenue_cents", "INTEGER"),
            ("SELECT '2026-02-31' AS report_date, 1 AS net_revenue_cents", "valid"),
            ("SELECT '2026-09-29' AS report_date, 1 AS net_revenue_cents FROM raw_orders", "duplicate dates"),
            ("""WITH RECURSIVE days(n) AS (
                    SELECT 1 UNION ALL SELECT n + 1 FROM days WHERE n < 100
                 ) SELECT date('2026-01-01', '+' || n || ' days') AS report_date,
                          n AS net_revenue_cents FROM days""", "row exercise bound"),
        ):
            with self.subTest(sql=sql):
                result = exercise.check(sql)
                self.assertFalse(result["passed"])
                self.assertIn(expected, result["checks"][0]["detail"])

    def test_empty_oversized_and_multiple_statements_are_rejected(self):
        for sql in ("", " " * 33000, CORRECT_SQL + " SELECT 1;"):
            with self.subTest(sql_length=len(sql)):
                self.assertFalse(exercise.check(sql)["passed"])

    def test_check_is_deterministic_and_hash_changes_with_artifact(self):
        first = exercise.check(exercise.starter(), incident=True)
        second = exercise.check(exercise.starter(), incident=True)
        self.assertEqual(first, second)
        modified = exercise.check(CORRECT_SQL + "\n-- revised artifact")
        self.assertTrue(modified["passed"])
        self.assertNotEqual(modified["artifact_hash"], exercise.check(CORRECT_SQL)["artifact_hash"])


if __name__ == "__main__":
    unittest.main()
