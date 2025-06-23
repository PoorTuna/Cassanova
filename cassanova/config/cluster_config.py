from typing import Optional, Any

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from pydantic import BaseModel, Field


class ClusterConnectionConfig(BaseModel):
    contact_points: list[str]
    port: int = Field(default=9042)
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    additional_kwargs: Optional[dict[str, Any]] = Field(default_factory=dict)


def generate_cluster_connection(cluster_config: ClusterConnectionConfig) -> Cluster:
    return Cluster(
        contact_points=cluster_config.contact_points, port=cluster_config.port,
        auth_provider=PlainTextAuthProvider(username=cluster_config.username,
                                            password=cluster_config.password),
        **cluster_config.additional_kwargs
    )
