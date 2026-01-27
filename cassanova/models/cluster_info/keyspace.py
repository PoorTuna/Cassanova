from typing import Annotated, Optional, Any

from pydantic import BaseModel, BeforeValidator, Field, computed_field

from cassanova.models.cluster_info.index import IndexInfo
from cassanova.models.cluster_info.table import TableInfo


class KeyspaceInfo(BaseModel):
    name: str
    replication: Annotated[
        Optional[Any],
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
    tables: list[TableInfo]
    indexes: list[IndexInfo] = Field(default_factory=dict)
    user_types: dict[str, Any] = Field(default_factory=dict)
    functions: dict[str, Any] = Field(default_factory=dict)
    aggregates: dict[str, Any] = Field(default_factory=dict)
    views: Optional[dict[str, Any]] = Field(default_factory=dict)
    graph_engine: Optional[Any] = None

    @computed_field
    @property
    def table_count(self) -> int:
        return len(self.tables)
