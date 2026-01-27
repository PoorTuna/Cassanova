from typing import Optional

from pydantic import BaseModel, Field

from cassanova.models.cluster_info.keyspace import KeyspaceInfo
from cassanova.models.cluster_info.node import NodeInfo
from cassanova.models.cluster_metrics import ClusterMetrics


class ClusterInfo(BaseModel):
    nodes: Optional[list[NodeInfo]] = Field(default_factory=NodeInfo)
    keyspaces: Optional[list[KeyspaceInfo]] = Field(default_factory=list)
    metrics: ClusterMetrics
