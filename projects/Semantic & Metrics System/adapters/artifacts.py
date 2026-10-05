from __future__ import annotations

import copy

from semantic.core import Registry, SemanticError, fingerprint, lineage, load_snapshot, meaning_fingerprint, snapshot_tables


def modeled_input(artifact: dict) -> dict:
    """Validate a Modeling-owned exported projection, without rerunning transformations."""
    snapshot_tables(artifact)
    return copy.deepcopy(artifact)


def artifact_export(target: str, registry: Registry, metric_id: str, version: str) -> dict:
    contract = registry.get(metric_id, version)
    header = {"contract_version": "semantic-integration-v1", "target": target, "scope": "synthetic_scenario", "connection": "artifact_contract", "live_connection": False, "definition_fingerprint": meaning_fingerprint(contract), "artifact_fingerprint": fingerprint(contract), "metric_id": metric_id, "version": version}
    if target == "modeling":
        return {**header, "producer_contract": "modeled-semantic-snapshot-v1", "snapshot": load_snapshot(), "required_grains": {"fct_orders": "order", "fct_order_refunds": "order", "dim_customers": "customer", "dim_products": "product"}, "policy": "Modeling owns transformations, order-version resolution, refund aggregation and identity mapping"}
    if target == "quality":
        return {**header, "requirements_contract": "semantic-check-requirements-v1", "requirements": [{"asset": "fct_orders", "expectation": "unique_non_null_order_id"}, {"asset": "fct_order_refunds", "expectation": "one_refund_aggregate_per_order_matching_snapshot_as_of"}], "policy": "Requirements are exported metadata; Quality owns execution and quality-event-v1/quality-gate-v1 truth. No quality PASS is fabricated by this export."}
    if target == "observability":
        graph = lineage(registry, metric_id, version)
        consumers = set(contract["consumers"])
        metric = f"{metric_id}@{version}"
        nodes = [{"id": n, "name": n, "node_type": "output" if n in consumers else "metric" if n == metric or "@" in n else "model", "layer": "output" if n in consumers or "@" in n else "unknown", "status": "UNKNOWN", "owner": contract["owner"] if n == metric else None, "metadata": {"definition_version": version, "scope": "synthetic_scenario", "live_connection": False} if n == metric else {}, "provenance": [{"source": "semantic-contract", "pointer": "/metrics/" + metric_id, "classification": "FACT", "note": "Declared synthetic contract, not operational measurements"}]} for n in graph["nodes"]]
        edges = [{"id": f"semantic-edge-{i}", "from_node": e["from"], "to_node": e["to"], "relationship_type": "depends_on", "evidence_source": {"source": "semantic-contract", "pointer": "/lineage", "classification": "FACT"}, "confidence": "declared", "inference_type": "FACT"} for i, e in enumerate(graph["edges"])]
        return {**header, "producer_contract": "data-map-v1", "artifact": {"contract_version": "data-map-v1", "system_id": "semantic-commerce", "name": "Governed synthetic commerce metrics", "nodes": nodes, "edges": edges, "sample": True}, "policy": "Observability owns measured freshness, dependency failures, incidents and affected-consumer evidence"}
    if target == "ae-lab":
        return {**header, "scenario_contract": "semantic-incident-reference-v1", "incident_id": "SEM-REVENUE-001", "opening": "Two dashboard totals disagree; authored technical checks report healthy. Request evidence and investigate.", "entry_point": "python3 -m semantic scenario SEM-REVENUE-001", "policy": "AE owns its learning orchestration and state; this is an explicit scenario reference, not an installed AE adapter"}
    if target == "fde-lab":
        return {**header, "requirements_contract": "semantic-discovery-handoff-v1", "metric_contract": contract, "required_discovery": ["business_decision", "accountable_business_owner", "grain", "identity", "time_basis", "timezone", "currency", "refund_policy", "acceptance"], "policy": "FDE owns customer WHY/WHO/WHAT; new customer definitions require their own approved contract. This fixture does not replace FIN-NET-1."}
    raise SemanticError("Unknown artifact integration target")
