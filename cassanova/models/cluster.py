from pydantic import BaseModel, Field

from cassanova.models.cluster_metrics import ClusterMetrics
from cassanova.models.keyspace import KeyspaceInfo
from cassanova.models.node import NodeInfo


class ClusterInfo(BaseModel):
    nodes: list[NodeInfo] | None = Field(default_factory=NodeInfo)  # type: ignore[arg-type]
    keyspaces: list[KeyspaceInfo] | None = Field(default_factory=list)
    metrics: ClusterMetrics
