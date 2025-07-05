from typing import Any, Annotated, Optional

from pydantic import BaseModel, BeforeValidator, Field

from cassanova.models.cluster_info.index import IndexInfo


class TableColumnInfo(BaseModel):
    name: str
    cql_type: str
    is_static: bool
    is_reversed: bool


class TableInfo(BaseModel):
    name: str
    partition_key: list[Any]
    clustering_key: Annotated[
        list[Any],
        BeforeValidator(lambda v: ['N/A'] if not v else v)
    ]
    columns: dict[str, TableColumnInfo]
    indexes: Optional[list[IndexInfo]] = Field(default_factory=list)
    options: dict[str, Any]
    comparator: Optional[Any] = None
    triggers: dict[str, Any] = Field(default_factory=list)
    views: Optional[dict[str, Any]] = Field(default_factory=dict)
    virtual: bool
    is_compact_storage: bool
    extensions: Optional[dict[str, Any]] = Field(default_factory=dict)
