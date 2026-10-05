from __future__ import annotations

from typing import Literal

from pydantic import Field

from .contracts import Contract, DataContract, Dataset
from .engine import value_matches


class CompatibilityPolicy(Contract):
    allow_optional_additions: bool = True
    allow_type_widening: bool = False
    require_data_for_null_tightening: bool = True
    allow_nullable_relaxation: bool = False
    semantic_change: Literal["breaking", "review"] = "breaking"


class CompatibilityRequest(Contract):
    before: DataContract
    after: DataContract
    policy: CompatibilityPolicy = Field(default_factory=CompatibilityPolicy)
    compatible_data: Dataset | None = None


def compare_contracts(request: CompatibilityRequest) -> dict:
    before, after, policy = request.before, request.after, request.policy
    changes = []

    def add(kind, subject, classification, reason):
        changes.append({"kind": kind, "subject": subject, "classification": classification, "reason": reason})
    if (before.id, before.dataset_id) != (after.id, after.dataset_id):
        add("identity", after.id, "BREAKING", "Different contract/dataset identity requires an explicit new consumer agreement.")
    if before.grain != after.grain:
        add("grain", "row meaning", "BREAKING", "Declared row meaning changed, even if keys still look unique.")
    if before.primary_key != after.primary_key:
        add("key", "primary key", "BREAKING", "Key definition changed.")
    if before.semantic_meaning != after.semantic_meaning or before.currency != after.currency:
        add("semantics", "measure meaning", "BREAKING" if policy.semantic_change == "breaking" else "REVIEW", "Structural checks cannot establish semantic equivalence.")
    old, new = {c.name: c for c in before.columns}, {c.name: c for c in after.columns}
    for name, column in old.items():
        if name not in new:
            add("removed", name, "BREAKING", "A removal or rename invalidates existing column references.")
            continue
        nxt = new[name]
        if column.data_type != nxt.data_type:
            widening = column.data_type == "INTEGER" and nxt.data_type == "DECIMAL" and nxt.precision - nxt.scale >= 19
            add("type", name, "ADDITIVE" if widening and policy.allow_type_widening else "BREAKING", "Type conversion is policy dependent; consumer compatibility is not guaranteed by a cast.")
        elif column.data_type == "DECIMAL" and (column.precision, column.scale) != (nxt.precision, nxt.scale):
            widening = nxt.scale >= column.scale and nxt.precision - nxt.scale >= column.precision - column.scale
            add("decimal_shape", name, "ADDITIVE" if widening and policy.allow_type_widening else "BREAKING", "Decimal precision and scale changed.")
        if column.nullable and not nxt.nullable:
            data = request.compatible_data
            proof = (data is not None and data.id == after.dataset_id and data.rows is not None and len(data.rows) > 0 and
                     all(name in r and r[name] is not None and value_matches(r[name], nxt) for r in data.rows))
            classification = "ADDITIVE" if proof else "REVIEW" if not policy.require_data_for_null_tightening else "BREAKING"
            add("nullable_to_required", name, classification, "Current compatible non-null data supports rollout; future producers still need enforcement." if proof else "Nullability tightening has no complete compatible-data proof.")
        if not column.nullable and nxt.nullable:
            add("nullability_relaxed", name, "ADDITIVE" if policy.allow_nullable_relaxation else "BREAKING", "Consumers that assumed a value may now receive NULL.")
        if not column.required and nxt.required:
            add("presence_tightened", name, "BREAKING", "A previously optional column is now required.")
        if column.required and not nxt.required:
            add("presence_relaxed", name, "BREAKING", "Consumers promised this column's presence may now receive data without it.")
        if column.description != nxt.description:
            add("description", name, "REVIEW", "Description changed; verify whether this is a semantic change.")
    for name, column in new.items():
        if name not in old:
            additive = not column.required and column.nullable and policy.allow_optional_additions
            add("added", name, "ADDITIVE" if additive else "BREAKING", "Optional additions are compatible only for consumers whose policy allows extras; required additions need rollout planning.")
    if [r.model_dump(mode="json") for r in before.relationships] != [r.model_dump(mode="json") for r in after.relationships]:
        add("relationships", "foreign keys", "BREAKING", "Relationship obligations changed.")
    if [r.model_dump(mode="json") for r in before.rules] != [r.model_dump(mode="json") for r in after.rules]:
        add("rules", "quality expectations", "REVIEW", "Validation or acceptance policy changed; inspect thresholds, severity and blocking.")
    status = "BREAKING" if any(c["classification"] == "BREAKING" for c in changes) else "REVIEW" if any(c["classification"] == "REVIEW" for c in changes) else "COMPATIBLE"
    return {"contract_version": "contract-compatibility-v1", "status": status,
            "changes": changes, "policy": policy.model_dump(mode="json"), "classification": "FACT",
            "limitation": "Deterministic structural policy analysis; it does not prove semantic safety or every consumer's behavior."}
