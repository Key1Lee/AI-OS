from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ImportRequest(StrictRequest):
    system_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$')
    name: str = Field(min_length=1,max_length=150)
    manifest: dict
    run_results: dict | None = None
    catalog: dict | None = None
    freshness: dict | None = None


class GraphQuery(StrictRequest):
    operation: Literal['get_node','upstream','downstream','direct_parents','direct_children','impact','shortest_path','all_paths','column_lineage','failed_path','affected_outputs','changed_nodes']
    node_id: str | None = Field(default=None,max_length=256)
    start: str | None = Field(default=None,max_length=256)
    end: str | None = Field(default=None,max_length=256)
    column: str | None = Field(default=None,max_length=256)


class InvestigationQuery(StrictRequest):
    system_id: str
    node_id: str
