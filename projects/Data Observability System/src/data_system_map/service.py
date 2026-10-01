from __future__ import annotations

from data_system_map.adapters.dbt import DbtAdapter
from data_system_map.contracts import GraphSnapshot
from data_system_map.graph import Graph
from data_system_map.repository import MetadataStore

LAYERS = ["source", "staging", "transformation", "mart", "output", "unknown"]


class DataSystemService:
    def __init__(self, store: MetadataStore):
        self.store = store

    def import_dbt(self, system_id, name, manifest, **artifacts) -> GraphSnapshot:
        # Normalize fully before the write transaction. Adapter errors leave the
        # previous system pointer and every historic snapshot unchanged.
        snapshot = DbtAdapter().ingest(system_id, name, manifest, **artifacts)
        return self.store.put(snapshot)

    def snapshot(self, system_id: str, snapshot_id=None) -> GraphSnapshot:
        return self.store.get(system_id, snapshot_id)

    def _status(self, snapshot, node, reveal_diagnostics):
        if reveal_diagnostics and node.status not in {"FAILED", "WARNING"}:
            if any(o.node_id == node.id and o.actual is not None and o.expected is not None and o.actual != o.expected for o in snapshot.observations):
                return "WARNING"
        return node.status

    def graph(self, system_id: str, *, snapshot_id=None, reveal_diagnostics=False, level="overview", focus=None, layer=None) -> dict:
        snapshot = self.snapshot(system_id, snapshot_id)
        graph = Graph(snapshot)
        public_nodes = [n for n in snapshot.nodes if n.node_type != "test"]
        stages = [{"id": key, "name": {"source":"Sources", "staging":"Staging", "transformation":"Transformations", "mart":"Marts", "output":"Business outputs", "unknown":"Unclassified"}[key],
                   "count": sum(n.layer == key for n in public_nodes),
                   "classification": "INFERENCE" if any(n.layer == key and n.metadata.get('layer_classification')=='INFERENCE' for n in public_nodes) else "FACT",
                   "failed": sum(n.layer == key and n.status == "FAILED" for n in public_nodes)} for key in LAYERS if any(n.layer == key for n in public_nodes)]
        stage_edges = sorted({(graph.nodes[e.from_node].layer, graph.nodes[e.to_node].layer) for e in snapshot.edges if e.relationship_type == "depends_on" and graph.nodes[e.from_node].layer != graph.nodes[e.to_node].layer})
        selected = []
        if level == "models":
            if focus:
                graph.get_node(focus)
                ids = {focus, *graph.direct_parents(focus), *graph.direct_children(focus)}
                selected = [n for n in public_nodes if n.id in ids]
            elif layer:
                selected = [n for n in public_nodes if n.layer == layer]
            else:
                selected = public_nodes
        if level not in {"overview", "models"}:
            raise ValueError("Choose overview or models.")
        selected.sort(key=lambda n: (LAYERS.index(n.layer), n.name, n.id))
        # Reserve a slot for the node the user selected before bounding neighbors.
        prioritized = sorted(selected, key=lambda n: n.id != focus) if focus else selected
        ids = {n.id for n in prioritized[:14]}
        visible_nodes = [n for n in selected if n.id in ids]
        return {"contract_version": snapshot.contract_version, "system_id": system_id, "name": snapshot.name, "snapshot_id": snapshot.snapshot_id,
                "sample": snapshot.sample, "level": level, "stages": stages, "stage_edges": [{"from": a, "to": b} for a,b in stage_edges],
                "nodes": [{"id": n.id, "name": n.name, "node_type": n.node_type, "layer": n.layer, "layer_classification": n.metadata.get("layer_classification", "FACT"), "status": self._status(snapshot,n,reveal_diagnostics), "grain": n.grain} for n in visible_nodes],
                "edges": [e.model_dump() for e in snapshot.edges if e.relationship_type == "depends_on" and e.from_node in ids and e.to_node in ids],
                "total_nodes": len(public_nodes), "visible_count": len(ids), "truncated": len(selected) > 14,
                "issues": [i.model_dump() for i in snapshot.issues], "ai_available": False}

    def node(self, system_id, key, *, snapshot_id=None, reveal_diagnostics=False) -> dict:
        snapshot = self.snapshot(system_id, snapshot_id)
        graph = Graph(snapshot)
        node = graph.get_node(key)
        result = node.model_dump()
        result['status'] = self._status(snapshot, node, reveal_diagnostics)
        result['inputs'] = [self._summary(graph.nodes[k]) for k in graph.direct_parents(key)]
        result['outputs'] = [self._summary(graph.nodes[k]) for k in graph.direct_children(key)]
        result['tests'] = [t.model_dump() for t in snapshot.tests if t.node_id == key]
        result['executions'] = [e.model_dump() for e in snapshot.executions if e.node_id == key]
        # Explicit node inspection legitimately retrieves that node's recorded
        # measurements in either audience, without a root-cause designation.
        result['observations'] = [o.model_dump() for o in snapshot.observations if o.node_id == key]
        result['impact'] = graph.impact(key)
        result['recent_changes'] = self.changed_nodes(system_id, snapshot_id=snapshot_id, key=key)
        result['unknowns'] = [label for label,value in [('Grain',node.grain),('Primary key',node.primary_keys),('Owner',node.owner),('SQL',node.sql)] if value is None]
        return result

    @staticmethod
    def _summary(node):
        return {"id": node.id, "name": node.name, "node_type": node.node_type}

    def relation(self, system_id, key, direction, *, snapshot_id=None) -> dict:
        graph = Graph(self.snapshot(system_id, snapshot_id))
        direct = graph.direct_parents(key) if direction == "upstream" else graph.direct_children(key)
        total = graph.upstream(key) if direction == "upstream" else graph.downstream(key)
        return {"node_id": key, "direction": direction, "direct": [self._summary(graph.nodes[k]) for k in direct],
                "transitive": [self._summary(graph.nodes[k]) for k in total if k not in direct], "classification": "FACT", "basis": "Declared artifact dependencies; not observed row movement."}

    def impact(self, system_id, key, *, snapshot_id=None):
        graph = Graph(self.snapshot(system_id, snapshot_id))
        return {k: [self._summary(graph.nodes[n]) for n in values] for k,values in graph.impact(key).items()}

    def changed_nodes(self, system_id, *, snapshot_id=None, key=None) -> dict:
        history = self.store.history(system_id)
        identity = snapshot_id or self.snapshot(system_id).snapshot_id
        index = next((i for i,h in enumerate(history) if h['id'] == identity), None)
        if index is None or index == 0:
            return {"available": False, "message": "No prior imported snapshot; recent Git changes are unavailable.", "nodes": [], "classification": "FACT"}
        old = {n.id:n.model_dump() for n in self.snapshot(system_id, history[index-1]['id']).nodes}
        new = {n.id:n.model_dump() for n in self.snapshot(system_id, identity).nodes}
        changed = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k) and (key is None or k == key))
        return {"available": True, "nodes": changed, "classification": "FACT", "message": "Metadata differs from the previous imported snapshot. This is correlation, not causation or a Git diff."}

    def incidents(self, system_id, *, snapshot_id=None) -> list[dict]:
        snapshot = self.snapshot(system_id, snapshot_id)
        return [{"id": n.id, "node_id": n.id, "name": n.name, "status": n.status, "classification": "FACT",
                 "summary": "An associated test or recorded execution failed. Inspect the evidence to distinguish them."}
                for n in snapshot.nodes if n.status == "FAILED" and n.node_type != "test"]

    def investigate(self, system_id, key, *, snapshot_id=None, reveal_diagnostics=False) -> dict:
        snapshot = self.snapshot(system_id, snapshot_id)
        graph = Graph(snapshot)
        graph.get_node(key)
        if graph.nodes[key].status != 'FAILED':
            raise ValueError('This node has no recorded execution or test failure. Inspect its node evidence instead.')
        visible = graph.failed_path(key)
        relevant_ids = [n for n in visible.pop('node_ids') if graph.nodes[n].node_type != 'test']
        priority = list(dict.fromkeys([key, *graph.direct_parents(key), *graph.direct_children(key), *graph.impact(key)['affected_outputs'], *relevant_ids]))
        ids = set(priority[:14])
        visible['nodes'] = [{**self._summary(graph.nodes[n]), 'layer': graph.nodes[n].layer, "status": self._status(snapshot, graph.nodes[n], reveal_diagnostics)} for n in relevant_ids if n in ids]
        visible['edges'] = [e for e in visible['edges'] if e['from_node'] in ids and e['to_node'] in ids]
        visible.update(total_nodes=len(relevant_ids), truncated=len(relevant_ids)>14)
        result = {"classification": "FACT", "observed_failure": key, "failure_path": visible,
                  "why": "Recorded execution or test evidence reports failure; root cause has not been proved.",
                  "evidence": [t.model_dump() for t in snapshot.tests if t.node_id == key and t.status == 'FAILED'],
                  "execution_evidence": [e.model_dump() for e in snapshot.executions if e.node_id == key and e.status == 'FAILED'],
                  "impact": self.impact(system_id,key,snapshot_id=snapshot_id)}
        if not reveal_diagnostics:
            result['message'] = "Assessment-safe failure view. Inspect nodes and recorded tests to gather evidence. No automatic cause or investigation hint is supplied."
            return result
        relevant = {key, *graph.upstream(key)}
        bad = [o for o in snapshot.observations if o.node_id in relevant and o.expected is not None and o.actual is not None and o.actual != o.expected]
        comparable = [o for o in snapshot.observations if o.node_id in relevant and o.expected is not None and o.actual is not None]
        bad_nodes = {o.node_id for o in bad}
        earliest = sorted(n for n in bad_nodes if not set(graph.upstream(n)) & bad_nodes)
        incomplete = any(i.code in {'cycle','missing_dependency','dependency_conflict','invocation_mismatch'} for i in snapshot.issues)
        candidate = earliest[0] if len(earliest) == 1 and not incomplete else None
        last_good = []
        if candidate:
            anomalies = [o for o in bad if o.node_id == candidate]
            for parent in graph.direct_parents(candidate):
                if any(g.node_id == parent and g.actual == g.expected and any(g.evidence_type == b.evidence_type and g.comparison_key == b.comparison_key and g.observation_id == b.observation_id and g.expected == b.expected for b in anomalies) for g in comparable):
                    last_good.append(parent)
            if not last_good:
                candidate = None
        result.update(first_suspicious_node=candidate, last_known_good=last_good if candidate else [], first_bad_node=None,
            inference={"classification":"INFERENCE", "message":"Earliest observed anomaly among comparable recorded checks; this does not prove a root cause." if candidate else "An earliest suspicious node cannot be established from comparable checks."},
            observations=[o.model_dump() for o in comparable],
            uncertainty=["First bad node cannot yet be established.", "Unmeasured branches and changes may still matter.", "A successful build does not validate grain or business correctness."],
            next_step="Inspect the recorded failure and direct inputs, identify a check that distinguishes your hypothesis, then verify a repair with that check.")
        return result

    def explain(self, system_id, *, snapshot_id=None, reveal_diagnostics=False):
        snapshot = self.snapshot(system_id, snapshot_id)
        stages = self.graph(system_id,snapshot_id=snapshot_id)['stages']
        steps = []
        for stage in stages:
            members = [n for n in snapshot.nodes if n.layer==stage['id'] and n.node_type!='test']
            descriptions = '; '.join(n.name + ': ' + (n.description or 'purpose unknown') for n in members[:3])
            sources = sorted({n.source_system for n in members if n.source_system})
            prefix = 'Declared inputs from '+', '.join(sources)+'. ' if stage['id']=='source' and sources else ''
            steps.append({'layer':stage['id'],'title':stage['name'],'node_ids':[n.id for n in members],
                          'classification':stage['classification'],'text':prefix+descriptions})
        return {"provider":"deterministic", "ai_available":False, "classification":"FACT",
                "message":"This tour follows declared metadata. No AI service was called.",
                "steps":steps}
