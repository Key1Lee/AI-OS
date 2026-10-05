import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from lab.contracts import PRIVATE_FIELDS, load_scenario, validate_scenario
from lab.engine import Engine, LabError, match_score
from lab.store import Store, fresh_state
from tests.test_exercise import CORRECT_SQL


PROJECT = Path(__file__).resolve().parent.parent


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.scenario = load_scenario()
        self.state = fresh_state(self.scenario)
        self.engine = Engine(self.scenario, self.state, self.directory)

    def release_with_prerequisites(self, key):
        for parent in self.scenario["evidence"][key]["requires"]:
            if parent not in self.state["released"]:
                self.release_with_prerequisites(parent)
        return self.engine.investigate(key)

    def review_latest(self, kind, text, citations, concept=None, dimension=None):
        self.engine.submit(kind, text, citations)
        submission = self.state["submissions"][-1]["id"]
        self.engine.review(submission, "demonstrated", "Inspected the cited evidence and causal reasoning.",
                           concept=concept, dimension=dimension, tutor="Test tutor")
        return submission

    def reach_prototype(self):
        self.engine.start()
        self.release_with_prerequisites("business-workflow")
        self.release_with_prerequisites("semantic-contract")
        self.review_latest("frame", "Finance loses review time while metric owners disagree; trace the workflow first.",
                           ["business-workflow"], dimension="Discovery")
        self.assertEqual(self.state["phase"], "DISCOVERY")
        self.review_latest("requirements", "Use the approved UTC cent contract; confirm acceptance and source ownership.",
                           ["semantic-contract"], dimension="Requirements")
        self.assertEqual(self.state["phase"], "SCOPED")
        self.review_latest("design", "Source events flow through a current-state model to a scoped aggregate; test a small fixture first.",
                           ["semantic-contract"], concept="data-grain", dimension="System Design")
        self.assertEqual(self.state["phase"], "PROTOTYPING")
        self.engine.build()

    def reach_deployment(self, additional_debug_concept=None):
        self.reach_prototype()
        source = self.directory / "workspace" / "revenue.sql"
        source.write_text(CORRECT_SQL)
        self.engine.test()
        self.review_latest("evaluate", "The fixture proves monetary invariants; system role probes and pilot value remain separate.",
                           [self.state["events"][-1]["id"]], concept="data-grain")
        self.assertEqual(self.state["phase"], "HARDENING")
        self.engine.break_system()
        self.assertIn("FAIL", self.engine.test())
        self.engine.investigate("incident delivery log")
        (self.directory / "workspace" / "incident.sql").write_text(CORRECT_SQL)
        self.engine.test()
        self.assertTrue(self.state["incident_passed"])
        self.review_latest("debug", "A lost acknowledgment allows retained events to be replayed; identity must stabilize logical state.",
                           ["incident-logs", self.state["events"][-1]["id"]], concept="idempotency", dimension="Debugging")
        if additional_debug_concept:
            self.review_latest("debug", "Tied delivered versions multiply the current business grain; the replay regression verifies recovery.",
                               ["incident-logs"], concept=additional_debug_concept)
        self.review_latest("harden", "Use scoped authorization, freshness alarms, named ownership, bounded retries, and a limited rollback-ready pilot.",
                           ["incident-logs"], dimension="Reliability")
        self.assertEqual(self.state["phase"], "DEPLOYING")
        return self.directory / "workspace" / "incident.sql"

    def test_scenario_contract_validates_real_content(self):
        self.assertIs(validate_scenario(self.scenario), self.scenario)
        self.assertEqual(self.scenario["customer"], "Northstar Retail")
        for key in PRIVATE_FIELDS:
            self.assertIn(key, self.scenario)

    def test_stakeholder_releases_one_matching_topic(self):
        self.engine.start()
        output = self.engine.ask("finance", "What is net revenue, and who uses the workflow?")
        self.assertIn("[semantic-contract]", output)
        self.assertEqual(self.state["released"], ["semantic-contract"])
        self.assertNotIn(self.scenario["evidence"]["business-workflow"]["text"], output)
        self.assertEqual(sum(event["kind"] == "evidence_released" for event in self.state["events"]), 1)

    def test_locked_requested_artifact_reveals_nothing(self):
        self.engine.start()
        before = copy.deepcopy(self.state)
        with self.assertRaises(LabError):
            self.engine.investigate("warehouse-sample")
        self.assertEqual(self.state, before)
        output = self.engine.ask("data-engineer", "Show data sample rows")
        self.assertEqual(self.state["released"], [])
        self.assertNotIn(self.scenario["evidence"]["warehouse-sample"]["text"], output)
        self.assertNotIn("[warehouse-sample]", output)
        with self.assertRaises(LabError):
            self.engine.evidence("warehouse-sample")
        self.engine.ask("data-engineer", "Explain the source identity contract")
        output = self.engine.investigate("warehouse-sample")
        self.assertIn("[warehouse-sample]", output)
        self.assertEqual(set(self.state["released"]), {"source-contract", "warehouse-sample"})

    def test_exact_matching_avoids_embedded_substrings(self):
        self.assertEqual(match_score("A chair is nearby", ["ai"]), 0)
        self.assertEqual(match_score("Remodeling has started", ["model"]), 0)
        self.assertEqual(match_score("The contractual concern", ["contract"]), 0)
        self.assertGreater(match_score("NET-REVENUE, in UTC?", ["net revenue"]), 0)
        self.engine.start()
        output = self.engine.ask("cto", "The chair needs remodeling")
        self.assertEqual(self.state["released"], [])
        self.assertIn("more specific question", output)

    def test_public_views_never_project_private_fields(self):
        sentinel = "PRIVATE-SCENARIO-CANARY-9364"
        for key in PRIVATE_FIELDS:
            self.scenario[key] = sentinel
        outputs = [self.engine.start(), self.engine.diagram(), self.engine.evidence(),
                   self.engine.progress(), self.engine.graph(), self.engine.log()]
        outputs.extend(self.engine.open(key) for key in self.scenario["components"])
        outputs.append(self.engine.log())
        for output in outputs:
            self.assertNotIn(sentinel, output)
        self.assertIn(sentinel, self.engine.solution())
        self.assertEqual(self.state["events"][-1]["kind"], "solution_explicitly_requested")

    def test_hypothesis_and_recall_are_recorded_pending_review(self):
        self.engine.start()
        feedback = self.engine.submit("hypothesis", "I suspect a data contract mismatch; compare two paths before upgrading the model.")
        self.assertIn("YOU IDENTIFIED:", feedback)
        self.assertIn("YOU'RE MISSING:", feedback)
        self.assertEqual(self.state["phase"], "DISCOVERY")
        self.assertEqual(self.state["reviews"], [])
        self.assertEqual(self.state["submissions"][-1]["kind"], "hypothesis")
        self.engine.recall()
        pending = self.state["pending_recall"]
        self.assertIsNotNone(pending)
        prompt = self.engine.recall()
        self.assertIn(pending, prompt)
        self.assertEqual(self.state["pending_recall"], pending)
        self.engine.submit("recall", "A physical retained event row can differ from a logical order; inspect identity and versions.")
        self.assertEqual(self.state["submissions"][-1]["prompt"], pending)
        self.assertIsNone(self.state["pending_recall"])
        self.assertEqual(self.state["reviews"], [])
        self.assertNotIn("MASTERED", [record["state"] for record in self.state["concepts"].values()])
        with self.assertRaises(LabError):
            self.engine.submit("recall", "This answer has no requested prompt.")

    def test_stage_gates_prevent_phase_skips(self):
        actions = [self.engine.build, self.engine.test, self.engine.break_system,
                   self.engine.deploy, self.engine.pilot_evidence,
                   lambda: self.engine.submit("design", "Use a warehouse", ["semantic-contract"]),
                   lambda: self.engine.submit("measure", "It is faster", ["pilot-results"])]
        for action in actions:
            with self.subTest(action=action):
                before = copy.deepcopy(self.state)
                with self.assertRaises(LabError):
                    action()
                self.assertEqual(self.state, before)
        self.engine.start()
        self.release_with_prerequisites("semantic-contract")
        self.engine.submit("frame", "Facts and assumptions are distinguished.", ["semantic-contract"])
        self.engine.submit("requirements", "Acceptance follows the owner contract.", ["semantic-contract"])
        self.assertEqual(self.state["phase"], "DISCOVERY")
        with self.assertRaises(LabError):
            self.engine.build()
        with self.assertRaises(LabError):
            self.engine.submit("requirements", "Uncited acceptance")
        with self.assertRaises(LabError):
            self.engine.submit("hypothesis", "I know the cause", ["locked-unseen-artifact"])

    def test_complete_discovery_code_incident_measurement_loop(self):
        self.reach_prototype()
        broken = self.engine.test()
        self.assertIn("FAIL", broken)
        self.assertEqual(self.state["phase"], "PROTOTYPING")
        self.assertFalse(self.state["exercise"]["passed"])
        source = self.directory / "workspace" / "revenue.sql"
        source.write_text(CORRECT_SQL)
        self.assertIn("PASS", self.engine.test())
        self.assertEqual(self.state["phase"], "EVALUATING")
        self.review_latest("evaluate", "Mutations prove semantic invariants; business and role evaluations need independent evidence.",
                           [self.state["events"][-1]["id"]], concept="data-grain")
        self.assertEqual(self.state["phase"], "HARDENING")
        opening = self.engine.break_system()
        self.assertIn(self.scenario["incident"]["opening"], opening)
        self.assertNotIn("incident-logs", self.state["released"])
        self.assertEqual(source.read_text(), CORRECT_SQL)
        self.assertIn("FAIL", self.engine.test())
        self.assertFalse(self.state["incident_passed"])
        logs = self.engine.investigate("delivery incident logs")
        self.assertIn("incident-logs", self.state["released"])
        self.assertTrue(logs.strip())
        (self.directory / "workspace" / "incident.sql").write_text(CORRECT_SQL)
        self.assertIn("PASS", self.engine.test())
        self.assertTrue(self.state["incident_passed"])
        self.review_latest("debug", "Replay follows a lost acknowledgment; use stable identities to preserve results and monitor divergence.",
                           ["incident-logs", self.state["events"][-1]["id"]], concept="idempotency", dimension="Debugging")
        self.assertEqual(self.state["phase"], "HARDENING")
        self.review_latest("harden", "Name scope, support owner, alert, stop condition, fallback and rollback for the restricted pilot.",
                           ["incident-logs"], dimension="Reliability")
        self.assertEqual(self.state["phase"], "DEPLOYING")
        self.assertIn("SIMULATED PILOT", self.engine.deploy())
        self.assertEqual(self.state["phase"], "OPERATING")
        self.assertNotIn("pilot-results", self.state["released"])
        self.assertIn("pilot-results", self.engine.investigate("pilot adoption measurement"))
        self.review_latest("measure", "Compare timed reconciliation and adoption against the observed baseline; separate small sample limits.",
                           ["pilot-results", "business-workflow"], dimension="Business Impact")
        self.assertEqual(self.state["phase"], "MEASURING")
        self.review_latest("explain", "The corrected model stabilizes money; causal diagnosis avoids premature model replacement, while rollout remains bounded.",
                           ["pilot-results", "incident-logs"], dimension="Communication")
        self.assertEqual(self.state["phase"], "RETROSPECTIVE")
        self.assertNotIn("MASTERED", [record["state"] for record in self.state["concepts"].values()])

    def test_failed_or_superseded_review_does_not_unlock_scope(self):
        self.engine.start()
        self.release_with_prerequisites("semantic-contract")
        first = self.review_latest("frame", "First framing", ["semantic-contract"])
        self.engine.review(first, "developing", "The cause is still asserted without evidence.", tutor="Test tutor")
        self.review_latest("requirements", "Owner-approved contract", ["semantic-contract"])
        self.assertEqual(self.state["phase"], "DISCOVERY")
        self.engine.review(first, "demonstrated", "The revised causal evidence supports this framing.", tutor="Test tutor")
        self.assertEqual(self.state["phase"], "SCOPED")

    def test_new_unreviewed_frame_supersedes_older_approval(self):
        self.engine.start()
        self.release_with_prerequisites("semantic-contract")
        self.review_latest("frame", "Initial framing", ["semantic-contract"])
        self.engine.submit("frame", "New framing changes the proposed intervention.", ["semantic-contract"])
        self.review_latest("requirements", "Owner-approved contract", ["semantic-contract"])
        self.assertEqual(self.state["phase"], "DISCOVERY")
        self.assertFalse(self.engine.reviewed("frame"))

    def test_recall_review_concept_mismatch_is_atomic(self):
        self.engine.start()
        self.engine.recall()
        prompt_id = self.state["pending_recall"]
        actual_concept = next(prompt["concept"] for prompt in self.scenario["recall"] if prompt["id"] == prompt_id)
        wrong_concept = next(key for key in self.state["concepts"] if key != actual_concept)
        self.engine.submit("recall", "This reasoning addresses the actual requested prompt.")
        submission = self.state["submissions"][-1]["id"]
        before = copy.deepcopy(self.state)
        with self.assertRaises(LabError):
            self.engine.review(submission, "demonstrated", "Checked the answer.", concept=wrong_concept,
                               dimension="Curiosity", tutor="Test tutor")
        self.assertEqual(self.state, before)
        self.engine.review(submission, "demonstrated", "Explains the row identity from evidence.", concept=actual_concept,
                           dimension="Curiosity", tutor="Test tutor")
        self.assertEqual(self.state["concepts"][actual_concept]["state"], "UNDERSTOOD")
        self.assertEqual(self.state["performance"]["Curiosity"]["state"], "DEMONSTRATED")

    def test_repeated_reviews_do_not_fabricate_mastery_or_consistency(self):
        self.engine.start()
        self.engine.recall()
        prompt_id = self.state["pending_recall"]
        concept = next(prompt["concept"] for prompt in self.scenario["recall"] if prompt["id"] == prompt_id)
        self.engine.submit("recall", "The logical business identity differs from a retained physical delivery.")
        submission = self.state["submissions"][-1]["id"]
        for _ in range(3):
            self.engine.review(submission, "demonstrated", "This one answer explains its causal mechanism.",
                               concept=concept, dimension="Data Systems", tutor="Test tutor")
        self.assertEqual(self.state["concepts"][concept]["state"], "UNDERSTOOD")
        self.assertEqual(self.state["performance"]["Data Systems"]["state"], "DEMONSTRATED")
        self.engine.review(submission, "developing", "The cited identifier still needs clarification.",
                           concept=concept, dimension="Data Systems", tutor="Test tutor")
        self.assertEqual(self.state["concepts"][concept]["state"], "EXPOSED")
        self.assertEqual(self.state["performance"]["Data Systems"]["state"], "DEVELOPING")

    def test_distinct_transfers_prove_mastery_and_revised_assessment_retracts_it(self):
        self.reach_deployment(additional_debug_concept="data-grain")
        concepts = {"data-grain", "idempotency"}
        for concept in concepts:
            self.assertEqual(self.state["concepts"][concept]["state"], "DEBUGGED")
        self.engine.deploy()
        self.engine.investigate("pilot measurement")
        self.review_latest("measure", "Compare the timed pilot workflow with its customer-approved baseline and limits.",
                           ["pilot-results"])
        self.review_latest("explain", "Separate the verified monetary repair from unproven rollout reliability; transfer the identity principles.",
                           ["pilot-results", "incident-logs"])
        self.assertEqual(self.state["phase"], "RETROSPECTIVE")

        transfers = {concept: set() for concept in concepts}
        reviewed_answers = {}
        for _ in range(len(self.scenario["recall"])):
            self.engine.recall()
            prompt = next(item for item in self.scenario["recall"] if item["id"] == self.state["pending_recall"])
            self.engine.submit("recall", "Preserve a stable business identity across repeated physical events; verify the new workflow with a counterexample.")
            if prompt["concept"] in concepts and prompt["transfer"]:
                concept = prompt["concept"]
                submission = self.state["submissions"][-1]["id"]
                self.engine.review(submission, "demonstrated", "Inspected application of the causal principle to this distinct workflow.",
                                   concept=concept, tutor="Test tutor")
                reviewed_answers[concept] = submission
                transfers[concept].add(prompt["id"])
                expected = "MASTERED" if len(transfers[concept]) >= 2 else "TRANSFERRED"
                self.assertEqual(self.state["concepts"][concept]["state"], expected)
        self.assertTrue(all(len(prompts) >= 2 for prompts in transfers.values()))
        self.assertEqual(self.state["phase"], "MASTERED")

        submission = reviewed_answers["idempotency"]
        self.engine.review(submission, "developing", "The agent retry answer still assumes success without durable outcome evidence.",
                           concept="idempotency", tutor="Test tutor")
        self.assertEqual(self.state["concepts"]["idempotency"]["state"], "EXPOSED")
        self.assertEqual(self.state["concepts"]["data-grain"]["state"], "MASTERED")
        self.assertEqual(self.state["phase"], "RETROSPECTIVE")
        self.engine.review(submission, "demonstrated", "The revised answer uses durable identity and verifies the prior result before retrying.",
                           concept="idempotency", tutor="Test tutor")
        self.assertEqual(self.state["concepts"]["idempotency"]["state"], "MASTERED")
        self.assertEqual(self.state["phase"], "MASTERED")

    def test_deploy_refuses_artifact_changed_after_replay_test(self):
        source = self.reach_deployment()
        source.write_text("SELECT '2026-09-29' AS report_date, 1 AS net_revenue_cents")
        before = copy.deepcopy(self.state)
        with self.assertRaises(LabError):
            self.engine.deploy()
        self.assertEqual(self.state["phase"], "DEPLOYING")
        self.assertFalse(any(event["kind"] == "simulated_pilot_deployed" for event in self.state["events"]))
        self.assertEqual(self.state, before)

    def test_non_destructive_reset_is_deterministic(self):
        store = Store(self.directory)
        self.engine.start()
        self.engine.ask("finance", "Define net revenue")
        store.write(self.state)
        workspace = self.directory / "workspace"
        workspace.mkdir()
        (workspace / "revenue.sql").write_text("-- preserve my unfinished work\n")
        first = store.reset(self.scenario)
        self.assertEqual(first, fresh_state(self.scenario))
        self.assertEqual(store.read(self.scenario), first)
        archive = self.directory / "history" / "reset-0001"
        self.assertEqual((archive / "workspace" / "revenue.sql").read_text(), "-- preserve my unfinished work\n")
        self.assertEqual(json.loads((archive / "state.json").read_text()), self.state)
        second = store.reset(self.scenario)
        self.assertEqual(first, second)
        first_engine = Engine(self.scenario, first, self.directory)
        second_engine = Engine(self.scenario, second, self.directory)
        self.assertEqual(first_engine.start(), second_engine.start())
        self.assertEqual(first, second)

    def test_cli_persists_between_processes_and_reset_preserves_work(self):
        def run_cli(*arguments):
            result = subprocess.run([sys.executable, "-m", "lab", "--state-dir", str(self.directory), *arguments],
                                    cwd=PROJECT, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

        opening = run_cli("next")
        self.assertIn("Northstar", opening)
        self.assertEqual(json.loads((self.directory / "state.json").read_text())["phase"], "DISCOVERY")
        response = run_cli("ask", "finance", "Define net revenue")
        self.assertIn("[semantic-contract]", response)
        listing = run_cli("evidence")
        self.assertIn("semantic-contract", listing)
        state_before = json.loads((self.directory / "state.json").read_text())
        self.assertEqual(state_before["released"], ["semantic-contract"])
        workspace = self.directory / "workspace"
        workspace.mkdir()
        (workspace / "notes.txt").write_text("Learner reasoning is retained.")
        reset_opening = run_cli("reset")
        self.assertEqual(opening, reset_opening)
        fresh = json.loads((self.directory / "state.json").read_text())
        expected = fresh_state(self.scenario)
        Engine(self.scenario, expected, self.directory).start()
        self.assertEqual(fresh, expected)
        self.assertEqual((self.directory / "history" / "reset-0001" / "workspace" / "notes.txt").read_text(),
                         "Learner reasoning is retained.")


if __name__ == "__main__":
    unittest.main()
