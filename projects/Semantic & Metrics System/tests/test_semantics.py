from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from adapters.artifacts import artifact_export, modeled_input
from semantic.core import Registry, SemanticError, evaluate, explain, lineage, load_catalog, load_snapshot, meaning_fingerprint
from semantic.scenario import Scenario

ROOT = Path(__file__).resolve().parents[1]


def request(metric="net_revenue", consumer="api", start="2026-09-30", end="2026-10-02", dimensions=None):
    return {"contract_version": "semantic-query-v1", "metric_id": metric, "version": "1.0.0", "consumer": consumer, "start": start, "end": end, "dimensions": dimensions or []}


def sign(contract):
    contract["approval"] = {"owner": contract["owner"], "evidence": "test-authored-owner", "scope": "synthetic_scenario", "approved_at": "2026-09-01T00:00:00Z", "meaning_fingerprint": meaning_fingerprint(contract)}


class ContractTests(unittest.TestCase):
    def test_four_metrics_explicit_entities_dimensions_measures(self):
        registry = Registry()
        self.assertEqual(registry.validate()["metrics"], 4)
        self.assertEqual(set(registry.catalog["entities"]), {"Order", "Customer", "Product"})
        for metric in registry.catalog["metrics"]:
            self.assertEqual(metric["grain"], "order")
            self.assertTrue(metric["owner"])
            self.assertTrue(metric["time_dimension"])

    def test_missing_owner_or_extra_field_rejected(self):
        for change in ({"owner": " "}, {"owner": None}, {"warehouse_sql": "select * from source"}):
            catalog = load_catalog()
            catalog["metrics"][0].update(change)
            with self.assertRaises(SemanticError):
                Registry(catalog)

    def test_contract_formula_and_declared_evaluator_agree(self):
        catalog = load_catalog()
        catalog["metrics"][1]["formula"] = "gross_order_value"
        sign(catalog["metrics"][1])
        with self.assertRaisesRegex(SemanticError, "formula"):
            Registry(catalog)

    def test_approval_covers_meaning_owner_and_scope(self):
        for field, value in (("time_dimension", "created_at"), ("owner", "Platform")):
            catalog = load_catalog()
            catalog["metrics"][0][field] = value
            with self.assertRaises(SemanticError):
                Registry(catalog)
        catalog = load_catalog()
        catalog["metrics"][0]["approval"]["scope"] = "production"
        with self.assertRaises(SemanticError):
            Registry(catalog)

    def test_duplicate_metric_version_rejected(self):
        catalog = load_catalog()
        catalog["metrics"].append(copy.deepcopy(catalog["metrics"][0]))
        with self.assertRaisesRegex(SemanticError, "unambiguous"):
            Registry(catalog)

    def test_missing_dependency_rejected(self):
        catalog = load_catalog()
        catalog["metrics"][1]["dependencies"] = ["gross_revenue@9.0.0"]
        sign(catalog["metrics"][1])
        with self.assertRaisesRegex(SemanticError, "Missing metric dependency"):
            Registry(catalog)

    def test_dependency_cycle_rejected(self):
        catalog = load_catalog()
        catalog["metrics"][0]["dependencies"] = ["net_revenue@1.0.0"]
        sign(catalog["metrics"][0])
        with self.assertRaisesRegex(SemanticError, "cycle"):
            Registry(catalog)

    def test_dependency_grain_or_time_incompatible(self):
        catalog = load_catalog()
        catalog["metrics"][0]["time_dimension"] = "created_at"
        sign(catalog["metrics"][0])
        with self.assertRaisesRegex(SemanticError, "incompatible time_dimension"):
            Registry(catalog)

    def test_same_version_cannot_change_meaning(self):
        registry = Registry()
        contract = registry.get("orders")
        contract["time_dimension"] = "created_at"
        sign(contract)
        with self.assertRaisesRegex(SemanticError, "overwrite"):
            registry.register(contract)

    def test_breaking_revision_requires_major_version_and_migration(self):
        registry = Registry()
        original = registry.get("orders")
        revision = copy.deepcopy(original)
        revision.update(version="1.1.0", previous_version="1.0.0", change_note="Move from fulfillment to booking time", compatibility="breaking", consumer_migration=["dashboard_a", "dashboard_b", "api", "ai", "sql"], effective_from="2026-10-05T00:00:00Z", time_dimension="created_at", status="PROPOSED", approval=None)
        with self.assertRaisesRegex(SemanticError, "major"):
            registry.register(revision)
        revision["version"] = "2.0.0"
        registry.register(revision)
        with self.assertRaises(SemanticError):
            registry.get("orders", "2.0.0")
        for stage in ("REVIEWED", "APPROVED", "ACTIVE"):
            approval = None
            if stage == "APPROVED":
                sign(revision)
                approval = revision["approval"]
            registry.transition("orders", "2.0.0", stage, approval)
        self.assertEqual(registry.get("orders", "1.0.0")["time_dimension"], "fulfilled_at")
        self.assertEqual(registry.get("orders", "2.0.0")["time_dimension"], "created_at")
        with self.assertRaisesRegex(SemanticError, "ambiguous"):
            registry.get("orders")

    def test_lifecycle_steps_and_deprecation(self):
        registry = Registry()
        registry.transition("orders", "1.0.0", "DEPRECATED")
        with self.assertRaises(SemanticError):
            registry.get("orders", "1.0.0")
        with self.assertRaises(SemanticError):
            registry.transition("orders", "1.0.0", "ACTIVE")

    def test_metadata_bindings_cannot_lie_about_sources_or_identity(self):
        for section, key, field, value in (("entities", "Customer", "identifier", "email"), ("measures", "gross_order_value", "field", "refund_amount_cents"), ("dimensions", "region", "source", "fct_orders")):
            catalog = load_catalog()
            catalog[section][key][field] = value
            with self.assertRaises(SemanticError):
                Registry(catalog)

    def test_asset_lineage_cycle_rejected(self):
        catalog = load_catalog()
        catalog["assets"]["orders_raw"]["parents"] = ["fct_orders"]
        with self.assertRaisesRegex(SemanticError, "cycle"):
            Registry(catalog)


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.snapshot = Registry(), load_snapshot()

    def test_known_results_independent_business_expectations(self):
        for metric, integer in (("gross_revenue", 870_000_000), ("net_revenue", 820_000_000), ("orders", 2), ("active_customers", 2)):
            self.assertEqual(evaluate(self.registry, self.snapshot, request(metric))["rows"][0]["integer_value"], integer)

    def test_chicago_midnight_differs_from_utc_date(self):
        rows = evaluate(self.registry, self.snapshot, request(dimensions=["date"]))["rows"]
        self.assertEqual(rows, [{"date": "2026-09-30", "value": "3800000.00", "integer_value": 380_000_000}, {"date": "2026-10-01", "value": "4400000.00", "integer_value": 440_000_000}])

    def test_different_created_time_version_cannot_be_substituted(self):
        catalog = load_catalog()
        for metric in catalog["metrics"]:
            metric["time_dimension"] = "created_at"
            sign(metric)
        result = evaluate(Registry(catalog), self.snapshot, request())
        self.assertEqual(result["rows"][0]["integer_value"], 460_000_000)
        self.assertNotEqual(result["definition_fingerprint"], evaluate(self.registry, self.snapshot, request())["definition_fingerprint"])

    def test_one_order_multiple_refunds_must_be_modeled_before_semantics(self):
        bad = copy.deepcopy(self.snapshot)
        bad["tables"]["fct_order_refunds"]["rows"].append(copy.deepcopy(bad["tables"]["fct_order_refunds"]["rows"][0]))
        with self.assertRaisesRegex(SemanticError, "fanout"):
            evaluate(self.registry, bad, request())

    def test_item_fanout_and_duplicate_dimension_rejected(self):
        for asset in ("fct_orders", "dim_customers", "dim_products"):
            bad = copy.deepcopy(self.snapshot)
            bad["tables"][asset]["rows"].append(copy.deepcopy(bad["tables"][asset]["rows"][0]))
            with self.assertRaisesRegex(SemanticError, "fanout"):
                evaluate(self.registry, bad, request())

    def test_dimension_compatibility_and_safe_slicing(self):
        result = evaluate(self.registry, self.snapshot, request(dimensions=["region", "product_category"]))
        self.assertEqual(sum(r["integer_value"] for r in result["rows"]), 820_000_000)
        with self.assertRaisesRegex(SemanticError, "dimension"):
            evaluate(self.registry, self.snapshot, request("active_customers", dimensions=["product_category"]))

    def test_customer_identity_is_distinct_across_orders_not_emails(self):
        result = evaluate(self.registry, self.snapshot, request("active_customers", end="2026-10-04"))
        self.assertEqual(result["rows"][0]["integer_value"], 2)
        bad = copy.deepcopy(self.snapshot)
        bad["tables"]["fct_orders"]["rows"][0]["customer_id"] = "guest@example.test"
        with self.assertRaisesRegex(SemanticError, "identity mapping"):
            evaluate(self.registry, bad, request())

    def test_refund_as_of_currency_and_unknown_order_are_checked(self):
        for field, value in (("as_of", "2026-10-03T00:00:00Z"), ("currency", "EUR"), ("order_id", "UNKNOWN")):
            bad = copy.deepcopy(self.snapshot)
            bad["tables"]["fct_order_refunds"]["rows"][0][field] = value
            with self.assertRaises(SemanticError):
                evaluate(self.registry, bad, request())

    def test_order_and_refund_integer_cents_not_floats(self):
        bad = copy.deepcopy(self.snapshot)
        bad["tables"]["fct_orders"]["rows"][0]["gross_order_value_cents"] = 10.1
        with self.assertRaisesRegex(SemanticError, "integer cents"):
            evaluate(self.registry, bad, request())

    def test_end_exclusive_and_empty_window_zero(self):
        result = evaluate(self.registry, self.snapshot, request(end="2026-10-01"))
        self.assertEqual(result["rows"][0]["integer_value"], 380_000_000)
        result = evaluate(self.registry, self.snapshot, request(start="2026-10-02", end="2026-10-03"))
        self.assertEqual(result["rows"][0]["integer_value"], 0)

    def test_naive_event_time_and_unapproved_window_rejected(self):
        bad = copy.deepcopy(self.snapshot)
        bad["tables"]["fct_orders"]["rows"][0]["fulfilled_at"] = "2026-10-01T01:00:00"
        with self.assertRaisesRegex(SemanticError, "Naive"):
            evaluate(self.registry, bad, request())
        with self.assertRaises(SemanticError):
            evaluate(self.registry, self.snapshot, request(start="2026-01-01"))
        with self.assertRaises(SemanticError):
            evaluate(self.registry, self.snapshot, request(start="2026-08-31", end="2026-09-01"))

    def test_large_integer_and_negative_net_render_without_rounding(self):
        changed = copy.deepcopy(self.snapshot)
        changed["tables"]["fct_orders"]["rows"][0]["gross_order_value_cents"] = 10**40 + 93
        row = evaluate(self.registry, changed, request("gross_revenue", end="2026-10-01"))["rows"][0]
        self.assertEqual(row["value"], "100000000000000000000000000000000000000.93")
        changed["tables"]["fct_orders"]["rows"][0]["gross_order_value_cents"] = 100
        row = evaluate(self.registry, changed, request(end="2026-10-01"))["rows"][0]
        self.assertEqual(row["value"], "-199999.00")

    def test_consumers_share_exact_rows_definition_catalog_and_sources(self):
        results = [evaluate(self.registry, self.snapshot, request(consumer=c)) for c in ("dashboard_a", "dashboard_b", "api", "ai", "sql")]
        for field in ("rows", "definition_fingerprint", "catalog_fingerprint", "source_fingerprint", "as_of", "version"):
            self.assertTrue(all(result[field] == results[0][field] for result in results))

    def test_consumer_cannot_invent_sql_or_formula(self):
        for field in ("formula", "business_definition", "sql", "time_dimension"):
            bad = request(consumer="ai")
            bad[field] = "consumer redefinition"
            with self.assertRaisesRegex(SemanticError, "Query accepts only"):
                evaluate(self.registry, self.snapshot, bad)

    def test_lineage_reaches_upstream_and_all_consumers(self):
        graph = lineage(self.registry, "net_revenue")
        self.assertTrue({"orders_raw", "refunds_raw", "fct_orders", "gross_order_value", "refund_amount", "net_revenue@1.0.0", "dashboard_a", "ai"} <= set(graph["nodes"]))
        self.assertIn("America/Chicago", explain(self.registry, "net_revenue"))


class ArtifactTests(unittest.TestCase):
    def test_modeled_artifact_and_all_adapters_are_explicitly_local(self):
        self.assertEqual(modeled_input(load_snapshot()), load_snapshot())
        for target in ("modeling", "quality", "observability", "ae-lab", "fde-lab"):
            result = artifact_export(target, Registry(), "net_revenue", "1.0.0")
            self.assertFalse(result["live_connection"])
            self.assertEqual(result["scope"], "synthetic_scenario")
        observability = artifact_export("observability", Registry(), "net_revenue", "1.0.0")["artifact"]
        self.assertEqual(observability["contract_version"], "data-map-v1")
        self.assertTrue(all(n["status"] == "UNKNOWN" for n in observability["nodes"]))
        nodes = {n["id"] for n in observability["nodes"]}
        self.assertTrue(all(e["from_node"] in nodes and e["to_node"] in nodes for e in observability["edges"]))


class ScenarioTests(unittest.TestCase):
    def investigate(self, scenario):
        scenario.predict("I want to compare what each report guarantees, beginning with row grain and health evidence.")
        for artifact in ("health", "models", "data", "dashboard-a", "dashboard-b", "finance-owner", "time-policy", "identity-policy"):
            scenario.inspect(artifact)
        scenario.diagnose("The queries measure different things; Finance owns the decision. Passing technical checks does not choose a business definition.")

    def test_opening_does_not_leak_diagnosis_or_formulas(self):
        with tempfile.TemporaryDirectory() as temp:
            opening = Scenario(temp).opening()
            self.assertIn("$8.7M", opening)
            self.assertNotIn("SUM(", opening)
            self.assertNotIn("semantic drift", opening.lower())
            self.assertNotIn("fulfilled_at", opening)
            self.assertNotIn("net_revenue", opening)

    def test_requested_evidence_only_and_prerequisites(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Scenario(temp)
            with self.assertRaises(SemanticError):
                scenario.inspect("finance-owner")
            scenario.predict("What do technical PASS reports establish?")
            with self.assertRaisesRegex(SemanticError, "prerequisites"):
                scenario.inspect("finance-owner")
            health = scenario.inspect("health")
            self.assertNotIn("SUM(", health["content"])
            self.assertEqual(scenario.state["inspected"], ["health"])
            with self.assertRaises(SemanticError):
                scenario.apply()

    def test_learner_wrong_owner_definition_is_not_automatically_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Scenario(temp)
            self.investigate(scenario)
            proposal = Registry().get("net_revenue")
            proposal["status"], proposal["approval"] = "PROPOSED", None
            proposal["timezone"] = "UTC"
            with self.assertRaises(SemanticError):
                scenario.propose(proposal)

    def test_complete_vertical_slice_and_unassessed_recall(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Scenario(temp)
            self.investigate(scenario)
            draft = scenario.template()
            self.assertEqual(draft["formula"], "")
            self.assertEqual(draft["time_dimension"], "")
            proposal = Registry().get("net_revenue")
            proposal["status"], proposal["approval"] = "PROPOSED", None
            scenario.propose(proposal)
            scenario.apply()
            report = Scenario(temp).verify()
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["consumers"]), 5)
            self.assertEqual(len(report["regression_guards"]), 4)
            scenario = Scenario(temp)
            recall = scenario.recall("My independent recollection still needs tutor assessment.")
            self.assertEqual(recall["assessment"], "unassessed_practice")
            self.assertEqual(scenario.state["stage"], "TRANSFER_PENDING")
            self.assertEqual(Registry().get("net_revenue")["status"], "ACTIVE")

    def test_concurrent_state_update_does_not_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Scenario(temp), Scenario(temp)
            first.predict("Investigate modeled grain")
            with self.assertRaisesRegex(SemanticError, "changed since read"):
                second.predict("Another session")
            self.assertEqual(Scenario(temp).state["hypothesis"], "Investigate modeled grain")

    def test_contradictory_prose_cannot_receive_fixture_owner_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            scenario = Scenario(temp)
            self.investigate(scenario)
            proposal = Registry().get("net_revenue")
            proposal["status"], proposal["approval"] = "PROPOSED", None
            proposal["business_definition"] = "Gross revenue before refunds; refunds do not reduce this metric."
            with self.assertRaisesRegex(SemanticError, "including its prose"):
                scenario.propose(proposal)

    def test_cli_subprocess_failure_exit_and_query(self):
        result = subprocess.run([sys.executable, "-m", "semantic", "query", "net_revenue", "--consumer", "ai", "--start", "2026-09-30", "--end", "2026-10-02"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["rows"][0]["integer_value"], 820_000_000)
        result = subprocess.run([sys.executable, "-m", "semantic", "query", "net_revenue", "--start", "2026-09-30", "--end", "2026-10-02", "--dimensions", "email"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("dimension", result.stderr)


if __name__ == "__main__":
    unittest.main()
