from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IndexInfo(BaseModel):
    name: str | None = None
    table: str | None = Field(default=None, alias="table_name")
    kind: str
    index_options: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)
