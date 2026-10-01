from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from data_system_map.contracts import Column, DataEdge, DataNode, Execution, GraphSnapshot, IncidentEvidence, Issue, Provenance, TestResult
from data_system_map.graph import Graph
from data_system_map.security import redact


class ArtifactError(ValueError):
    """Safe adapter error; never include uploaded values or SQL in the message."""


def object_at(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ArtifactError(f"{label} must be a JSON object.")
    return value


def array_at(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ArtifactError(f"{label} must be a JSON array.")
    return value


def text(value: Any, label: str, *, optional=False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or len(value) > 160000 or (not optional and not value):
        raise ArtifactError(f"{label} must be a string.")
    return redact(value)


def identity(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:-]{0,255}", value) or redact(value) != value:
        raise ArtifactError("Artifact resource identity is invalid.")
    return value


def timestamp(value: Any, label: str) -> str | None:
    value = text(value, label, optional=True)
    if value is not None:
        try:
            # Keep the calendar ISO representation understood by browser dates;
            # Python also accepts basic/week dates and offsets with seconds.
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?)?", value):
                raise ValueError
            datetime.fromisoformat(value)
        except ValueError:
            raise ArtifactError("Artifact timestamps must be ISO 8601 strings or unknown.") from None
    return value


def pointer(value: str) -> str:
    if not isinstance(value, str) or redact(value) != value:
        raise ArtifactError("Artifact metadata keys must not contain secret patterns.")
    return value.replace('~', '~0').replace('/', '~1')


def status(value: str) -> str:
    return {"success": "HEALTHY", "pass": "HEALTHY", "warn": "WARNING", "fail": "FAILED", "error": "FAILED", "runtime error": "FAILED"}.get(value.lower(), "UNKNOWN")


class DbtAdapter:
    def ingest(self, system_id: str, name: str, manifest: dict, *, run_results=None, catalog=None, freshness=None) -> GraphSnapshot:
        system_id = identity(system_id)
        name = text(name, "system.name")
        manifest = object_at(manifest, "manifest")
        metadata = object_at(manifest.get("metadata", {}), "manifest.metadata")
        version = metadata.get("dbt_schema_version")
        if version is not None and (not isinstance(version, str) or not re.search(r"/dbt/manifest/v(?:[7-9]|1[0-2])\.json$", version)):
            raise ArtifactError("Unsupported manifest schema. This adapter reads the v7–v12 resource subset.")
        nodes, resources, edges, executions, tests, observations, issues = {}, {}, [], [], [], [], []
        artifacts = {}

        def provenance(source, location, classification="FACT", note=None):
            return Provenance(source=source, pointer=location, classification=classification,
                              timestamp=artifacts.get(source, {}).get("generated_at"), note=note)

        def record_artifact(source, artifact):
            meta = object_at(artifact.get("metadata", {}), source + ".metadata")
            artifacts[source] = {key: timestamp(meta.get(key), source + ".metadata." + key) if key == "generated_at" else text(meta.get(key), source + ".metadata." + key, optional=True)
                                 for key in ["dbt_schema_version", "dbt_version", "generated_at", "invocation_id", "producer"]}
            artifacts[source]["sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True, allow_nan=False).encode()).hexdigest()

        record_artifact("manifest.json", manifest)
        if version is None:
            issues.append(Issue(code="schema_version_unknown", message="Manifest schema version is unknown; only the supported resource subset was validated.", provenance=provenance("manifest.json", "/metadata")))
        type_mapping = {"source": "source", "model": "model", "test": "test", "exposure": "output", "metric": "metric", "seed": "seed", "snapshot": "snapshot", "analysis": "analysis"}
        for group in ["nodes", "sources", "metrics", "exposures"]:
            for key, raw in sorted(object_at(manifest.get(group, {}), "manifest." + group).items()):
                identity(key)
                raw = object_at(raw, "manifest resource")
                if raw.get("unique_id", key) != key:
                    raise ArtifactError("Manifest resource key and unique_id disagree.")
                kind = raw.get("resource_type", {"sources": "source", "metrics": "metric", "exposures": "exposure"}.get(group))
                kind = text(kind, "resource.resource_type")
                if kind not in type_mapping:
                    issues.append(Issue(code="unsupported_resource", message="A resource type is not represented in this release.", node_id=key, provenance=provenance("manifest.json", "/" + group + "/" + pointer(key))))
                    continue
                if key in resources:
                    raise ArtifactError("A resource identity appears in multiple manifest groups.")
                resources[key] = raw
                location = "/" + group + "/" + pointer(key)
                meta = object_at(raw.get("meta") or {}, "resource.meta")
                config_meta = object_at(object_at(raw.get("config") or {}, "resource.config").get("meta") or {}, "resource.config.meta")
                meta = {**config_meta, **meta}
                node_name = text(raw.get("name"), "resource.name")
                layer = meta.get("layer")
                layer_classification = "FACT"
                if layer is None:
                    layer = "source" if kind == "source" else "output" if kind in {"exposure", "metric"} else "staging" if node_name.startswith("stg_") else "mart" if node_name.startswith("mart_") else "transformation" if node_name.startswith(("int_", "fct_", "dim_")) else "unknown"
                    layer_classification = "FACT" if kind in {"source", "exposure", "metric"} else "INFERENCE"
                if not isinstance(layer, str) or layer not in {"source", "staging", "transformation", "mart", "output", "unknown"}:
                    raise ArtifactError("Resource layer metadata is invalid.")
                keys = meta.get("primary_keys")
                if keys is not None and (not isinstance(keys, list) or any(not isinstance(k, str) for k in keys)):
                    raise ArtifactError("Declared primary_keys must be an array of column names.")
                keys = [text(k, "resource.primary_key") for k in keys] if keys is not None else None
                columns = []
                for column_key, declaration in object_at(raw.get("columns") or {}, "resource.columns").items():
                    declaration = object_at(declaration, "column declaration")
                    column_name = text(declaration.get("name", column_key), "column.name")
                    nullable = object_at(declaration.get("meta") or {}, "column.meta").get("nullable")
                    if nullable is not None and type(nullable) is not bool:
                        raise ArtifactError("Declared nullable must be a boolean or unknown.")
                    columns.append(Column(name=column_name, data_type=text(declaration.get("data_type"), "column.data_type", optional=True), nullable=nullable,
                                          description=text(declaration.get("description"), "column.description", optional=True),
                                          provenance=[provenance("manifest.json", location + "/columns/" + pointer(column_key), note="Declared column metadata, not a live schema query.")]))
                nodes[key] = DataNode(id=key, name=node_name, namespace=text(raw.get("schema"), "resource.schema", optional=True), node_type=type_mapping[kind], layer=layer,
                    description=text(raw.get("description"), "resource.description", optional=True), grain=text(meta.get("grain"), "resource.meta.grain", optional=True),
                    primary_keys=keys, columns=columns, owner=text(meta.get("owner") if isinstance(meta.get("owner"), str) else None, "resource.owner", optional=True),
                    source_system=text(meta.get("source_system", raw.get("source_name")), "resource.source_system", optional=True),
                    sql=text(raw.get("raw_code", raw.get("raw_sql")), "resource.sql", optional=True), compiled_sql=text(raw.get("compiled_code", raw.get("compiled_sql")), "resource.compiled_sql", optional=True),
                    metadata={"materialization": text(object_at(raw.get("config") or {}, "resource.config").get("materialized"), "resource.materialization", optional=True), "layer_classification": layer_classification},
                    provenance=[provenance("manifest.json", location), provenance("manifest.json", location + "/meta/layer", layer_classification, "Layer declared in metadata." if layer_classification == "FACT" else "Layer inferred from the resource name; it can be wrong.")])
                custom = object_at(meta.get("data_system_map") or {}, "resource.meta.data_system_map")
                for observation in array_at(custom.get("observations", []), "resource observations"):
                    observation = object_at(observation, "observation")
                    if any(value is not None and type(value) not in {int, float, str} for value in [observation.get("expected"), observation.get("actual")]):
                        raise ArtifactError("Observation values must be scalar measurements or unknown.")
                    measurements = {field: observation.get(field) for field in ["expected", "actual"]}
                    for field, value in measurements.items():
                        if isinstance(value, str) and text(value, "observation." + field) != value:
                            # Removing sensitive values must not manufacture equal,
                            # comparable checks or a false last-known-good node.
                            measurements[field] = None
                            issues.append(Issue(code="redacted_measurement", node_id=key, message="A sensitive measurement was removed; comparison is unavailable.", provenance=provenance("manifest.json", location + "/meta/data_system_map/observations")))
                    observations.append(IncidentEvidence(node_id=key, evidence_type=text(observation.get("evidence_type"), "observation.evidence_type"), **measurements,
                        comparison_key=text(observation.get("comparison_key"), "observation.comparison_key", optional=True), observation_id=identity(observation.get("observation_id")),
                        provenance=provenance("manifest.json", location + "/meta/data_system_map/observations", note="Reported measurement; provenance identifies the producer.")))

        parent_map = object_at(manifest.get("parent_map", {}), "manifest.parent_map")
        for key, raw in resources.items():
            dependencies = object_at(raw.get("depends_on") or {}, "resource.depends_on")
            parents = array_at(dependencies.get("nodes", []), "resource.depends_on.nodes")
            parents = sorted({identity(value) for value in parents})
            if key in parent_map:
                mapped = sorted({identity(value) for value in array_at(parent_map[key], "manifest.parent_map entry")})
                if mapped != parents:
                    issues.append(Issue(code="dependency_conflict", node_id=key, message="parent_map and depends_on disagree. The graph uses explicit resource depends_on; both declarations remain identified by artifact hash and pointers.", provenance=provenance("manifest.json", "/parent_map/" + pointer(key))))
            for parent in parents:
                if parent not in nodes:
                    issues.append(Issue(code="missing_dependency", node_id=key, message="A declared parent is missing or unsupported; lineage is incomplete.", provenance=provenance("manifest.json", "/nodes/" + pointer(key) + "/depends_on/nodes", note="Unresolved resource: " + redact(parent))))
                    continue
                relation = "tests" if nodes[key].node_type == "test" else "depends_on"
                edges.append(DataEdge(id=hashlib.sha256(f"{parent}\0{key}\0{relation}".encode()).hexdigest()[:24], from_node=parent, to_node=key, relationship_type=relation,
                                      evidence_source=provenance("manifest.json", "/" + ("sources" if nodes[key].node_type == "source" else "exposures" if nodes[key].node_type == "output" else "metrics" if nodes[key].node_type == "metric" else "nodes") + "/" + pointer(key) + "/depends_on/nodes")))

        if catalog is not None:
            catalog = object_at(catalog, "catalog")
            record_artifact("catalog.json", catalog)
            for group in ["nodes", "sources"]:
                for key, raw in object_at(catalog.get(group, {}), "catalog." + group).items():
                    raw = object_at(raw, "catalog resource")
                    if key not in nodes:
                        issues.append(Issue(code="unknown_catalog_node", message="Catalog metadata references a resource outside this manifest.", provenance=provenance("catalog.json", "/" + group)))
                        continue
                    supplied = raw.get("columns", {})
                    supplied = list(object_at(supplied, "catalog.columns").values()) if isinstance(supplied, dict) else array_at(supplied, "catalog.columns")
                    for raw_column in supplied:
                        raw_column = object_at(raw_column, "catalog column")
                        name_value = text(raw_column.get("name"), "catalog column.name")
                        dtype = text(raw_column.get("type"), "catalog column.type", optional=True)
                        column = next((c for c in nodes[key].columns if c.name == name_value), None)
                        if column is None:
                            column = Column(name=name_value)
                            nodes[key].columns.append(column)
                        if column.data_type and dtype and column.data_type.lower() != dtype.lower():
                            issues.append(Issue(code="schema_conflict", node_id=key, message=f"Declared and catalog column types disagree for {name_value}: {column.data_type} / {dtype}.", provenance=provenance("catalog.json", "/" + group + "/" + pointer(key) + "/columns")))
                        column.data_type = dtype or column.data_type
                        column.provenance.append(provenance("catalog.json", "/" + group + "/" + pointer(key) + "/columns", note="Catalog-reported schema; no live warehouse query was made."))

        result_by_id = {}
        if run_results is not None:
            run_results = object_at(run_results, "run_results")
            record_artifact("run_results.json", run_results)
            manifest_invocation = artifacts["manifest.json"].get("invocation_id")
            result_invocation = artifacts["run_results.json"].get("invocation_id")
            if manifest_invocation and result_invocation and manifest_invocation != result_invocation:
                issues.append(Issue(code="invocation_mismatch", message="Manifest and run results come from different invocations. Current-code compatibility is unproven.", provenance=provenance("run_results.json", "/metadata/invocation_id")))
            operation = object_at(run_results.get("args") or {}, "run_results.args").get("which")
            if operation is not None:
                operation = text(operation, "run_results.args.which")
            for index, raw in enumerate(array_at(run_results.get("results"), "run_results.results")):
                raw = object_at(raw, "run result")
                key = identity(raw.get("unique_id"))
                if key in result_by_id:
                    raise ArtifactError("Multiple results for one resource require separate snapshots.")
                result_by_id[key] = raw
                if key not in nodes:
                    issues.append(Issue(code="unknown_execution_node", message="An execution result references a resource outside this manifest.", provenance=provenance("run_results.json", f"/results/{index}")))
                    continue
                reported = text(raw.get("status"), "run result.status")
                timing = [object_at(t, "run timing") for t in array_at(raw.get("timing", []), "run timing")]
                duration = raw.get("execution_time")
                if duration is not None and (type(duration) not in {int, float} or duration < 0):
                    raise ArtifactError("Execution time must be nonnegative or unknown.")
                executed = Execution(node_id=key, status=status(reported), reported_status=reported, operation=operation,
                    started_at=timestamp(timing[0].get("started_at"), "run timing.started_at") if timing else None,
                    completed_at=timestamp(timing[-1].get("completed_at"), "run timing.completed_at") if timing else None,
                    duration=duration, error=text(raw.get("message"), "run result.message", optional=True), provenance=provenance("run_results.json", f"/results/{index}"))
                executions.append(executed)
                nodes[key].status = executed.status if executed.status in {"FAILED", "WARNING"} or nodes[key].node_type == "test" or operation in {"run", "build", "seed", "snapshot", "retry"} else "UNKNOWN"
                if reported.lower() not in {"success", "pass", "warn", "fail", "error", "skipped", "runtime error"}:
                    issues.append(Issue(code="unknown_execution_status", node_id=key, message="An unrecognized execution status remains UNKNOWN.", provenance=executed.provenance))

        for key, node in nodes.items():
            if node.node_type != "test":
                continue
            raw, result = resources[key], result_by_id.get(key)
            attached = raw.get("attached_node")
            associated = sorted({edge.from_node for edge in edges if edge.to_node == key and edge.relationship_type == "tests"})
            targets = [attached] if attached in associated else associated
            ambiguous = len(targets) > 1
            test_meta = object_at(raw.get("test_metadata") or {}, "test_metadata")
            kwargs = object_at(test_meta.get("kwargs") or {}, "test_metadata.kwargs")
            test_column = kwargs.get("column_name", raw.get("column_name"))
            if test_column is not None:
                test_column = text(test_column, "test column")
            for target in targets:
                failures = result.get("failures") if result else None
                if failures is not None and (type(failures) is not int or failures < 0):
                    raise ArtifactError("Test failure count must be a nonnegative integer or unknown.")
                item = TestResult(node_id=target, test_id=key, test_name=node.name, status=node.status,
                    reported_status=text(result["status"], "test status") if result else "not_executed", severity=text(object_at(raw.get("config") or {}, "test.config").get("severity"), "test severity", optional=True),
                    failures=failures, column=test_column, association="ambiguous" if ambiguous else "confirmed", evidence=text(result.get("message"), "test message", optional=True) if result else None,
                    provenance=next((e.provenance for e in executions if e.node_id == key), provenance("manifest.json", "/nodes/" + pointer(key))))
                tests.append(item)
                for column in nodes[target].columns:
                    if column.name == test_column:
                        column.tests.append(key)
                if item.status == "FAILED":
                    nodes[target].status = "WARNING" if ambiguous and nodes[target].status != "FAILED" else "FAILED"
                elif item.status == "WARNING" and nodes[target].status != "FAILED":
                    nodes[target].status = "WARNING"

        if freshness is not None:
            freshness = object_at(freshness, "freshness")
            schema = str(object_at(freshness.get("metadata", {}), "freshness.metadata").get("dbt_schema_version", ""))
            source = "sources.json" if "/sources/" in schema else "freshness.json"
            record_artifact(source, freshness)
            for index, raw in enumerate(array_at(freshness.get("results"), "freshness.results")):
                raw = object_at(raw, "freshness result")
                key = identity(raw.get("unique_id"))
                if key not in nodes:
                    issues.append(Issue(code="unknown_freshness_node", message="Freshness result refers to an unknown resource.", provenance=provenance(source, f"/results/{index}")))
                    continue
                reported = text(raw.get("status"), "freshness.status")
                executions.append(Execution(node_id=key, status=status(reported), reported_status=reported, operation="freshness",
                    completed_at=timestamp(raw.get("snapshotted_at"), "freshness.snapshotted_at"), provenance=provenance(source, f"/results/{index}")))
                incoming = status(reported)
                if incoming == "FAILED" or (incoming == "WARNING" and nodes[key].status != "FAILED"):
                    nodes[key].status = incoming
                elif nodes[key].status == "UNKNOWN" and nodes[key].node_type == "source":
                    nodes[key].status = incoming

        snapshot = GraphSnapshot(system_id=system_id, name=name, nodes=sorted(nodes.values(), key=lambda n: n.id), edges=sorted(edges, key=lambda e: e.id),
            executions=executions, tests=tests, observations=observations, issues=issues, artifacts=artifacts, sample=metadata.get("sample") is True)
        for cycle in Graph(snapshot).cycles():
            snapshot.issues.append(Issue(code="cycle", message="A declared dependency cycle was detected.", node_id=cycle[0], provenance=provenance("manifest.json", "/nodes", note=" → ".join(cycle))))
        return snapshot
