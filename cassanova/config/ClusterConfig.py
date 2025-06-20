from typing import Optional, Any

from pydantic import BaseModel, Field


class ClusterConfig(BaseModel):
    cluster_name: str
    contact_points: list[str]
    port: int = Field(default=9042)
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    additional_kwargs: Optional[dict[str, Any]] = Field(default_factory=dict)
