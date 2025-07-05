from typing import Optional, Literal

from pydantic import BaseModel, Field


class ClusterMetrics(BaseModel):
    partitioner: Optional[str] = None
    name: str = Field(alias='cluster')
    snitch: str
    version: str
    rack_count: int
    dc_count: int
    cluster_size: Optional[str]
    total_nodes: int
    up_nodes: int
    down_nodes: int
    status: str
    version: str = 'N/A'
    is_fully_upgraded: bool = False
    technology: Literal['cassandra', 'scylla', 'dse']
