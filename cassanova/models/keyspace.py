from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, computed_field

from cassanova.models.index_info import IndexInfo
from cassanova.models.table import TableInfo


class KeyspaceInfo(BaseModel):
    name: str
    replication: Annotated[Any | None, BeforeValidator(lambda v: "N/A" if v is None else v)] = (
        Field(default="N/A")
    )
    durable_writes: Annotated[
        bool | str | None, BeforeValidator(lambda v: "N/A" if v is None else v)
    ] = Field(default="N/A")
    virtual: Annotated[bool | None, BeforeValidator(lambda v: False if v is None else v)] = Field(
        default=False
    )
    tables: list[TableInfo]
    indexes: list[IndexInfo] = Field(default_factory=dict)  # type: ignore[arg-type]
    user_types: dict[str, Any] = Field(default_factory=dict)
    functions: dict[str, Any] = Field(default_factory=dict)
    aggregates: dict[str, Any] = Field(default_factory=dict)
    views: dict[str, Any] | None = Field(default_factory=dict)
    graph_engine: Any | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def table_count(self) -> int:
        return len(self.tables)
