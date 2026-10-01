from typing import Protocol

from data_system_map.contracts import GraphSnapshot


class EnginePort(Protocol):
    def snapshot(self, system_id: str, snapshot_id: str | None = None) -> GraphSnapshot: ...
    def impact(self, system_id: str, key: str, *, snapshot_id: str | None = None) -> dict: ...


COMMERCE_SCENARIO = {
    "id": "commerce-grain-v1",
    "system_id": "commerce-demo",
    "title": "Finance's revenue report no longer reconciles",
    "brief": "The Executive Dashboard's revenue changed after a pipeline run. A quality check failed in the order fact model. Investigate the recorded system evidence, identify the earliest supported suspicion, assess impact, and propose a fix and verification plan. You may inspect nodes, schemas, SQL, recorded tests and lineage. No production system is connected.",
    "failure": "model.commerce.fct_orders",
    "suspect": "model.commerce.int_order_items",
    "upstream": "model.commerce.stg_orders",
    "grain": "one_row_per_order",
}
