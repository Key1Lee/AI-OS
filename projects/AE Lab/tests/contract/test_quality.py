"""Contract and real native integration checks; no replacement validator."""
from copy import deepcopy
import unittest

from lab.adapters.bridge import AdapterError
from lab.adapters.quality import NativeQualityAdapter

CLOCK = "2026-10-03T09:00:00+09:00"


def orders(count: int = 1000) -> list[dict]:
    return [{"order_id": f"ORD-{i:04d}", "customer_id": f"C-{i % 20:03d}",
             "status": "completed", "order_amount": "10.00", "currency": "USD",
             "ordered_at": CLOCK} for i in range(1, count + 1)]


class NativeQualityContractTests(unittest.TestCase):
    def setUp(self):
        self.adapter = NativeQualityAdapter()

    def test_complete_healthy_dataset_has_real_native_open_gates(self):
        rows = orders()
        before = deepcopy(rows)
        result = self.adapter.validate(rows, "quality-healthy", CLOCK)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["gate_open"])
        self.assertEqual((result["total_rows"], result["validated_rows"], result["distinct_keys"],
                          result["duplicate_extra"]), (1000, 1000, 1000, 0))
        self.assertEqual(rows, before)
        self.assertEqual(len(result["results"]), 5)
        for bundle in result["results"]:
            self.assertEqual(bundle["contract_version"], "quality-bundle-v1")
            self.assertEqual(bundle["run_id"], "quality-healthy")
            self.assertEqual(bundle["gate"]["publication"], "ELIGIBLE")
            self.assertTrue(all(check["status"] == "PASS" for check in bundle["results"]))
        self.assertTrue(all(event["contract_version"] == "quality-event-v1"
                            for event in result["events"]))

    def test_partial_write_plus_retry_detects_all_cross_input_duplicates(self):
        source = orders()
        result = self.adapter.validate(source[:700] + source, "quality-corrupt", CLOCK)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["gate_open"])
        self.assertEqual((result["total_rows"], result["validated_rows"], result["distinct_keys"],
                          result["duplicate_extra"], result["duplicate_affected"]),
                         (1700, 1700, 1000, 700, 1400))
        self.assertTrue(all(shard["rows"] <= 200 for shard in result["shards"]))
        self.assertTrue(any(event["rule_id"] == "contract_grain" and event["status"] == "FAIL"
                            for event in result["events"]))

    def test_duplicate_at_naive_chunk_boundary_cannot_escape(self):
        source = orders(201)
        result = self.adapter.validate(source + [source[0]], "quality-boundary", CLOCK)
        self.assertEqual(result["duplicate_extra"], 1)
        self.assertEqual(result["distinct_keys"], 201)
        self.assertFalse(result["gate_open"])

    def test_missing_key_preserves_unknown_and_withholds_publication(self):
        source = orders(2)
        del source[0]["order_id"]
        result = self.adapter.validate(source, "quality-unknown", CLOCK)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["gate_open"])
        self.assertIsNone(result["duplicate_extra"])
        self.assertIsNone(result["distinct_keys"])
        self.assertTrue(any(event["status"] == "UNKNOWN" for event in result["events"]))

    def test_wrong_schema_cannot_pass_despite_unique_keys(self):
        source = orders(2)
        source[0]["order_amount"] = 10.1
        result = self.adapter.validate(source, "quality-schema", CLOCK)
        self.assertEqual(result["duplicate_extra"], 0)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["gate_open"])

    def test_empty_dataset_cannot_pass(self):
        result = self.adapter.validate([], "quality-empty", CLOCK)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["gate_open"])
        self.assertEqual(result["validated_rows"], 0)

    def test_native_clock_rejection_is_an_explicit_error(self):
        with self.assertRaises(AdapterError):
            self.adapter.validate(orders(1), "quality-clock", "2026-10-03T09:00:00")

    def test_unrepresentable_key_group_does_not_split_and_falsely_pass(self):
        source = orders(1) * 201
        with self.assertRaisesRegex(AdapterError, "200-row limit"):
            self.adapter.validate(source, "quality-large-group", CLOCK)


if __name__ == "__main__":
    unittest.main()
