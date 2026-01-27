from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class IndexInfo(BaseModel):
    name: Optional[str] = None
    table: Optional[str] = Field(default=None, alias="table_name")
    kind: str
    index_options: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)
