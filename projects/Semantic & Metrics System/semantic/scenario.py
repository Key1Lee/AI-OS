from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from .core import DATA, Registry, SemanticError, evaluate, fingerprint, load_catalog, load_snapshot, meaning_fingerprint, read_json


class Scenario:
    """Local practice evidence, never a general scheduler or independent mastery grade."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.path = self.directory / "SEM-REVENUE-001.json"
        self.definition = read_json(DATA / "scenario.json")
        self.state = read_json(self.path) if self.path.exists() else {
            "contract_version": "semantic-practice-v1", "scenario": "SEM-REVENUE-001",
            "stage": "ASK", "inspected": [], "hypothesis": None, "diagnosis": None,
            "proposal": None, "registry": None, "verification": None, "recall_answers": None,
            "history": [], "assessment": "unassessed_practice",
        }
        self._loaded_fingerprint = fingerprint(self.state) if self.path.exists() else None

    def save(self, action: str):
        self.directory.mkdir(parents=True, exist_ok=True)
        lock = self.directory / ".semantic-state.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise SemanticError("Another local state write is in progress; retry after it completes") from exc
        try:
            os.close(descriptor)
            current = fingerprint(read_json(self.path)) if self.path.exists() else None
            if current != self._loaded_fingerprint:
                raise SemanticError("Session changed since read; reload before writing")
            self.state["history"].append({"action": action, "stage": self.state["stage"]})
            temp = self.directory / ".semantic-state.tmp"
            temp.write_text(json.dumps(self.state, indent=2) + "\n")
            temp.replace(self.path)
            self._loaded_fingerprint = fingerprint(self.state)
        finally:
            lock.unlink(missing_ok=True)

    def opening(self) -> str:
        return self.definition["architecture"] + "\n\n" + self.definition["opening"] + "\n\nChoose one evidence artifact: " + ", ".join(self.definition["artifacts"]) + "\nStage: " + self.state["stage"]

    def predict(self, text: str) -> dict:
        if not text.strip():
            raise SemanticError("Record your initial question or prediction")
        if self.state["stage"] != "ASK":
            raise SemanticError("Prediction is recorded before investigation; existing work is preserved")
        self.state["hypothesis"] = text
        self.state["stage"] = "INVESTIGATE"
        self.save("record_prediction")
        return {"stage": "INVESTIGATE", "assessment": "recorded_not_graded", "next": "Inspect one selected artifact. What claim can it support?"}

    def inspect(self, artifact: str) -> dict:
        if self.state["stage"] == "ASK":
            raise SemanticError("First record what you want to understand and why with scenario predict")
        if artifact not in self.definition["artifacts"]:
            raise SemanticError("Unknown evidence artifact")
        evidence = self.definition["artifacts"][artifact]
        missing = set(evidence["prerequisites"]) - set(self.state["inspected"])
        if missing:
            raise SemanticError("Inspect prerequisites first: " + ", ".join(sorted(missing)))
        if artifact not in self.state["inspected"]:
            self.state["inspected"].append(artifact)
            self.save("inspect:" + artifact)
        result = {"artifact_id": artifact, "title": evidence["title"], "content": evidence["content"], "scope": "authored_synthetic_evidence", "question": "What does this establish, and what remains unknown?"}
        if artifact == "data":
            result["snapshot"] = load_snapshot()
        return result

    def diagnose(self, text: str) -> dict:
        required = {"health", "models", "data", "dashboard-a", "dashboard-b", "finance-owner", "time-policy", "identity-policy"}
        missing = required - set(self.state["inspected"])
        if missing:
            raise SemanticError("Diagnosis requires investigation evidence: " + ", ".join(sorted(missing)))
        if self.state["stage"] != "INVESTIGATE" or not text.strip():
            raise SemanticError("Record a diagnosis after investigating, before design")
        self.state["diagnosis"] = text
        self.state["stage"] = "DESIGN"
        self.save("record_diagnosis")
        return {"stage": "DESIGN", "assessment": "unassessed_practice", "question": self.definition["diagnosis_question"], "next": "Create a proposed JSON contract with scenario template. A human tutor must assess your reasoning."}

    def template(self) -> dict:
        if self.state["stage"] != "DESIGN":
            raise SemanticError("Contract template opens after evidence and diagnosis")
        c = Registry().get("net_revenue", "1.0.0")
        c["status"], c["approval"] = "PROPOSED", None
        # Keep the discovered owner's exact prose; the learner must translate it
        # into executable identity, grain, recognition and calculation choices.
        for field in ("owner", "grain", "aggregation", "formula", "time_dimension", "timezone", "calendar", "refund_attribution"):
            c[field] = ""
        for field in ("measure", "dimensions", "upstream_assets", "dependencies"):
            c[field] = []
        c["filters"] = {"status": [], "currency": ""}
        c["currency"] = None
        return c

    def propose(self, contract: dict) -> dict:
        if self.state["stage"] != "DESIGN":
            raise SemanticError("Record diagnosis before proposing business meaning")
        if contract.get("metric_id") != "net_revenue" or contract.get("status") != "PROPOSED" or contract.get("approval") is not None:
            raise SemanticError("Submit a proposed net_revenue contract; approval belongs to its owner")
        catalog = load_catalog()
        expected = Registry(catalog).get("net_revenue", "1.0.0")
        catalog["metrics"] = [c for c in catalog["metrics"] if c["metric_id"] != "net_revenue"] + [copy.deepcopy(contract)]
        Registry(catalog)
        if meaning_fingerprint(contract) != meaning_fingerprint(expected):
            raise SemanticError("Proposal does not match the discovered synthetic owner definition, including its prose. The fixture owner cannot approve changed business meaning; a new owner-approved scenario contract is required.")
        self.state["proposal"], self.state["registry"] = copy.deepcopy(contract), catalog
        self.state["stage"] = "IMPLEMENT"
        self.save("record_proposal")
        return {"stage": "IMPLEMENT", "validation": "PASS", "assessment": "contract_structure_and_owner_constraints_only", "next": "Apply the proposal with the explicitly discovered synthetic owner approval evidence."}

    def apply(self) -> dict:
        if self.state["stage"] != "IMPLEMENT":
            raise SemanticError("A validated learner proposal is required before implementation")
        registry = Registry(self.state["registry"])
        proposal = self.state["proposal"]
        approval = {"owner": proposal["owner"], "evidence": "SEM-REVENUE-001/finance-owner (authored training artifact)", "scope": "synthetic_scenario", "approved_at": "2026-09-01T00:00:00Z", "meaning_fingerprint": meaning_fingerprint(proposal)}
        for stage in ("REVIEWED", "APPROVED", "ACTIVE"):
            registry.transition("net_revenue", proposal["version"], stage, approval if stage == "APPROVED" else None)
        self.state["registry"], self.state["stage"] = registry.catalog, "VERIFY"
        self.save("apply_scenario_local_contract")
        return {"stage": "VERIFY", "scope": "scenario_local_registry", "owner_approval": "synthetic_scenario", "consumers": "dashboard_a/dashboard_b/API/AI/SQL now request net_revenue@1.0.0", "next": "Run scenario verify to evaluate all consumers and regression guards."}

    def verify(self) -> dict:
        if self.state["stage"] not in {"VERIFY", "RECALL"}:
            raise SemanticError("Apply the contract before verification")
        registry, snapshot = Registry(self.state["registry"]), load_snapshot()
        window = self.definition["window"]
        results = [evaluate(registry, snapshot, {"contract_version": "semantic-query-v1", "metric_id": "net_revenue", "version": "1.0.0", "consumer": consumer, **window, "dimensions": []}) for consumer in ("dashboard_a", "dashboard_b", "api", "ai", "sql")]
        values = {r["rows"][0]["integer_value"] for r in results}
        definitions = {r["definition_fingerprint"] for r in results}
        sources = {r["source_fingerprint"] for r in results}
        passed = values == {820_000_000} and len(definitions) == len(sources) == 1
        guards = []
        for mutation in ("formula_override", "item_fanout", "missing_owner", "wrong_time"):
            try:
                if mutation == "formula_override":
                    bad = {"contract_version": "semantic-query-v1", "metric_id": "net_revenue", "version": "1.0.0", "consumer": "ai", **window, "dimensions": [], "formula": "SUM(raw_orders)"}
                    evaluate(registry, snapshot, bad)
                elif mutation == "item_fanout":
                    bad = copy.deepcopy(snapshot)
                    bad["tables"]["fct_orders"]["rows"].append(copy.deepcopy(bad["tables"]["fct_orders"]["rows"][0]))
                    evaluate(registry, bad, {"contract_version": "semantic-query-v1", "metric_id": "net_revenue", "version": "1.0.0", "consumer": "ai", **window, "dimensions": []})
                else:
                    bad = copy.deepcopy(registry.catalog)
                    c = next(c for c in bad["metrics"] if c["metric_id"] == "net_revenue")
                    c["owner" if mutation == "missing_owner" else "time_dimension"] = "" if mutation == "missing_owner" else "created_at"
                    Registry(bad)
                guards.append({"guard": mutation, "status": "FAIL"})
            except SemanticError:
                guards.append({"guard": mutation, "status": "PASS"})
        passed = passed and all(g["status"] == "PASS" for g in guards)
        report = {"status": "PASS" if passed else "FAIL", "consumers": results, "regression_guards": guards, "practice_assessment": "unassessed", "scope": "local_deterministic_fixture", "recall_questions": self.definition["recall_questions"] if passed else []}
        if passed:
            self.state["stage"] = "RECALL"
        self.state["verification"] = report
        self.save("verify_consumer_consistency")
        return report

    def recall(self, text: str | None = None) -> dict:
        if self.state["stage"] not in {"RECALL", "TRANSFER_PENDING"}:
            raise SemanticError("Verify the implementation before recall")
        if text is not None:
            if not text.strip():
                raise SemanticError("Record recall answers; they need independent tutor assessment")
            self.state["recall_answers"], self.state["stage"] = text, "TRANSFER_PENDING"
            self.save("record_unassessed_recall")
        return {"questions": self.definition["recall_questions"], "assessment": "unassessed_practice", "next": self.definition["next_concept"]}
