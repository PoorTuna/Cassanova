from typing import List, Optional, Annotated, OrderedDict, Any

from pydantic import BaseModel, computed_field, Field, ConfigDict, BeforeValidator

from cassanova.models.cluster_metrics import ClusterMetrics


class TableInfo(BaseModel):
    name: str
    partition_key: List[Any]
    clustering_key: List[Any]
    columns: dict[str, Any]
    indexes:  Optional[dict[str, str]] = {}
    options: dict[str, Any]
    comparator: Optional[dict] = None
    triggers: Any = []
    views: Optional[dict[str, dict]] = {}
    virtual: bool
    is_compact_storage: bool
    extensions: Optional[dict[str, Any]] = {}
    protocol_version: Optional[Any] = None


class KeyspaceInfo(BaseModel):
    name: str
    replication: Annotated[
        Optional[str],
        BeforeValidator(lambda v: 'N/A' if v is None else v)
    ] = Field(default='N/A')
    durable_writes: Annotated[
        Optional[bool | str],
        BeforeValidator(lambda v: 'N/A' if v is None else v)
    ] = Field(default='N/A')
    virtual: Annotated[
        Optional[bool],
        BeforeValidator(lambda v: False if v is None else v)
    ] = Field(default=False)
    tables: List[TableInfo]

    @computed_field
    @property
    def table_count(self) -> int:
        return len(self.tables)


class NodeInfo(BaseModel):
    name: str
    status: str
    load: Optional[str] = None
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    token_range: Optional[str] = None


class ClusterInfo(BaseModel):
    nodes: Optional[List[NodeInfo]] = Field(default_factory=list)
    keyspaces: Optional[List[KeyspaceInfo]] = Field(default_factory=list)
    metrics: ClusterMetrics

    model_config = ConfigDict(populate_by_name=True)
