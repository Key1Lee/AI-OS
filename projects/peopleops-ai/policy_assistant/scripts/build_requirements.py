"""Materialize the explicit mock BRD and acceptance map; this never generates test answers."""
import csv
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROWS = [
    ("HR-001", "Authenticate every assistant request", "Security", "employee", "Identity map and bearer authentication", "app/auth.py;app/identity.py", "test_authentication", "routing", "authentication_success", "No downstream call after failed authentication"),
    ("HR-002", "Return exact authorized synthetic PTO", "HR Operations", "employee", "Mock Workday PTO records", "app/workday_client.py;app/orchestrator.py", "test_self_pto", "grounding", "pto_exactness", "All authorized fixture balances exact; cross-user access denied"),
    ("HR-003", "Answer approved policy questions", "HR Policy Owner", "employee", "Governed mock document registry", "app/rag_search.py;app/response_builder.py", "test_policy_answer", "retrieval", "recall_at_5", "Recall@5 >= 0.95 on labeled applicable policies"),
    ("HR-004", "Enforce document and resource permissions", "Security", "employee", "Server-owned roles, groups, country and explicit scopes", "app/permissions.py;app/rag_search.py", "test_access_boundaries", "security", "unauthorized_exposure", "Zero observed unauthorized source or record exposures"),
    ("HR-005", "Select the correct workflow and source", "HR Service Desk", "employee", "Deterministic routing rules", "app/intent_router.py;app/orchestrator.py", "test_intent_routing", "routing", "routing_accuracy", "Routing accuracy >= 0.98 on independent labeled cases"),
    ("HR-006", "Return checkable evidence", "HR Policy Owner", "employee", "Immutable source versions and exact quotes", "app/response_builder.py", "test_exact_citations", "grounding", "citation_validity", "All citations resolve to current authorized source text"),
    ("HR-007", "Handle ambiguity, gaps and outages safely", "HR Service Desk", "employee", "Typed statuses and bounded error responses", "app/orchestrator.py;app/response_builder.py", "test_safe_failures", "grounding", "appropriate_abstention", "All unsupported, ambiguous and injected fault cases match expected status"),
    ("HR-008", "Govern the permissible document inventory", "HR Policy Owner", "policy administrator", "Independent approval metadata and content digests", "ingestion/validate_documents.py;ingestion/classify_documents.py", "test_registry_governance", "security", "unapproved_exposure", "No altered, unapproved, revoked or malicious source indexed as usable"),
    ("HR-009", "Record useful redacted operations evidence", "Operations", "operator", "Allowlisted JSON audit fields and aggregate metrics", "app/audit.py", "test_redacted_audit", "security", "sensitive_leakage", "Zero fixture secrets or employee identifiers in observed logs/errors"),
    ("HR-010", "Measure bounded local reliability and latency", "Operations", "operator", "Local machine and bounded read retries", "app/workday_client.py;evals/run_evaluations.py", "test_retry_bounds", "reliability", "local_mock_p95_ms", "Local mock p95 < 750 ms; production SLO remains proposed"),
    ("HR-011", "Enforce source freshness and policy lifecycle", "HR Policy Owner", "employee", "Versioned inventory, effective dates and source timestamps", "ingestion/index_documents.py;app/rag_search.py;app/workday_client.py", "test_current_versions", "retrieval", "outdated_exposure", "Zero obsolete, expired, future or stale source answers"),
    ("HR-012", "Reproduce functional and AI evaluation evidence", "Engineering", "developer", "pytest, independent JSONL labels and gated CI", "evals/run_evaluations.py;.github/workflows/ci.yaml", "test_evaluation_contract", "all", "required_gates", "All critical tests and deterministic evaluation gates pass"),
    ("HR-013", "Ingest bounded batches idempotently", "Engineering", "policy administrator", "SQLite transactions and immutable document version keys", "ingestion/run_pipeline.py;ingestion/index_documents.py", "test_idempotent_pipeline", "retrieval", "duplicate_active_records", "Reprocessing creates no duplicate active versions; changes require new approvals"),
    ("HR-014", "Add workflows behind clear adapter contracts", "Engineering", "developer", "Injected Workday, identity and retriever interfaces", "app/workday_client.py;app/orchestrator.py;app/models.py", "test_injected_adapters", "routing", "workflow_source_correctness", "The three core workflows use the expected injected source or no source"),
    ("HR-015", "Resist prompt injection and data leakage", "Security", "employee", "Hard authorization and untrusted evidence treatment", "app/permissions.py;app/orchestrator.py;ingestion/classify_documents.py", "test_adversarial_boundaries", "security", "critical_security_pass_rate", "All curated adversarial cases pass; no absolute-security claim"),
]


LAYER_ROWS = [('AC-LAB-001',
  'HR-009',
  'Each request shows actual stage outcomes/timings and only authorized source metadata',
  'app/diagnostics.py;app/orchestrator.py;app/main.py',
  'test_inspectors_describe_real_authorized_work',
  'security',
  'redacted_measured_trace'),
 ('AC-LAB-002',
  'HR-005',
  'Applied rule IDs resolve to executable server-owned YAML, with seven configured intents',
  'app/rules.py;app/intent_router.py;config/routing_rules.yaml',
  'test_yaml_routing_is_executable',
  'routing',
  'configured_routing_accuracy'),
 ('AC-LAB-003',
  'HR-012',
  'Authenticated dashboard job executes real pytest and publishes isolated actual JUnit/coverage results',
  'app/test_runner.py;app/lab_worker.py;app/enterprise_static/app.js',
  'test_dashboard_job_runs_real_pytest_process',
  'security',
  'backend_test_execution'),
 ('AC-LAB-004',
  'HR-007',
  'Switchable failures return expected safe statuses without mutating another request',
  'app/main.py;app/workday_client.py',
  'test_request_scoped_failures_are_real_and_isolated',
  'grounding',
  'fault_isolation'),
 ('AC-LAB-005',
  'HR-002',
  'PTO values originate from SQLite records; unchanged seed replay preserves stored edits',
  'app/enterprise_data.py;app/workday_client.py',
  'test_pto_comes_from_sqlite_and_unchanged_seed_preserves_edits',
  'grounding',
  'database_source_correctness'),
 ('AC-LAB-006',
  'HR-015',
  'Test execution requires an explicit lab grant and rejects commands, paths and unknown suites',
  'app/main.py;app/test_runner.py;config/security_policies.yaml',
  'test_test_runner_requires_explicit_permission_and_fixed_inputs',
  'security',
  'authorized_fixed_test_commands'),
 ('AC-LAB-007',
  'HR-010',
  'Jobs serialize, enforce deadlines and isolate reports; slow calls have measured stage latency',
  'app/test_runner.py;tests/performance/test_testing_performance.py',
  'test_job_lifecycle_serialization_and_tenant_scope',
  'grounding',
  'job_reliability'),
 ('AC-LAB-008',
  'HR-004',
  'Cached receipts cannot restore revoked delegation or removed inventory access',
  'app/main.py;app/identity.py',
  'test_receipt_cannot_restore_revoked_delegation',
  'security',
  'receipt_authority_binding')]


def main():
    requirements, criteria = [], []
    for rid, objective, stakeholder, persona, sources, implementation, test, dataset, metric, gate in ROWS:
        requirements.append({
            "id": rid, "approval_status": "proposed_mock_requirement", "objective": objective,
            "stakeholder": stakeholder, "user_story": f"As a fictional {persona}, I need to {objective.lower()} so HR support is verifiable and controlled.",
            "classification": "nonfunctional" if rid in ("HR-009", "HR-010", "HR-012", "HR-013", "HR-014", "HR-015") else "functional",
            "assumptions_and_dependencies": ["Synthetic fixtures only; no stakeholder approval inferred", sources],
            "authorized_sources": [sources], "implementation": implementation.split(";"),
            "acceptance_criteria": [rid.replace("HR-", "AC-")], "positive_scenario": objective,
            "negative_scenario": gate, "tests": [test], "evaluation_dataset": dataset,
            "metrics": [metric], "proposed_release_gate": gate,
        })
        criteria.append({"id": rid.replace("HR-", "AC-"), "requirement_id": rid, "assertion": gate,
                         "test_function": test, "status": "planned_until_executed", "evidence": "reports/release.json"})
    for ac, rid, assertion, implementation, test, dataset, metric in LAYER_ROWS:
        requirement = next(r for r in requirements if r["id"] == rid)
        for key, values in [("implementation", implementation.split(";")), ("tests", [test]), ("acceptance_criteria", [ac]), ("metrics", [metric])]:
            for value in values:
                if value not in requirement[key]:
                    requirement[key].append(value)
        criteria.append({"id": ac, "requirement_id": rid, "assertion": assertion, "test_function": test,
                         "status": "requires_current_executed_evidence", "evidence": "reports/release.json"})
    directory = ROOT / "requirements"
    directory.mkdir(exist_ok=True)
    (directory / "business_requirements.yaml").write_text(yaml.safe_dump({"approval": "All business decisions are mock proposals", "requirements": requirements}, sort_keys=False))
    (directory / "acceptance_criteria.yaml").write_text(yaml.safe_dump({"criteria": criteria}, sort_keys=False))
    with (directory / "traceability.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["requirement_id", "acceptance_id", "implementation", "test_function", "dataset", "metric", "release_gate"])
        for row in ROWS:
            rid, _, _, _, _, implementation, test, dataset, metric, gate = row
            writer.writerow([rid, rid.replace("HR-", "AC-"), implementation, test, dataset, metric, gate])
        for ac, rid, assertion, implementation, test, dataset, metric in LAYER_ROWS:
            writer.writerow([rid, ac, implementation, test, dataset, metric, "Current mapped regression tests and deterministic release gates pass"])
    print("Wrote 15 proposed requirements and 23 acceptance/traceability rows")


if __name__ == "__main__":
    main()
