from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field

from cassanova.models.index_info import IndexInfo


class TableColumnInfo(BaseModel):
    name: str
    cql_type: str
    is_static: bool
    is_reversed: bool


class TableInfo(BaseModel):
    name: str
    partition_key: list[Any]
    clustering_key: Annotated[list[Any], BeforeValidator(lambda v: v if v else ["N/A"])]
    columns: dict[str, TableColumnInfo]
    indexes: list[IndexInfo] | None = Field(default_factory=list)  # type: ignore[arg-type]
    options: dict[str, Any]
    comparator: Any | None = None
    triggers: dict[str, Any] = Field(default_factory=list)  # type: ignore[arg-type]
    views: dict[str, Any] | None = Field(default_factory=dict)
    virtual: bool
    is_compact_storage: bool
    extensions: dict[str, Any] | None = Field(default_factory=dict)
