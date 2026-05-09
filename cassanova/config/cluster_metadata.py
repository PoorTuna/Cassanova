from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ClusterMetadata(BaseModel):
    source: Literal["static", "k8s"] = "static"
    context: str | None = None
    discovered_at: datetime | None = None
    last_seen: datetime | None = None
    miss_count: int = 0
