from typing import Optional, Any

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from pydantic import BaseModel, Field


class ClusterCredentials(BaseModel):
    username: str
    password: str


class ClusterConnectionConfig(BaseModel):
    contact_points: list[str]
    port: int = Field(default=9042)
    credentials: Optional[ClusterCredentials] = Field(default=None)
    jmx_credentials: Optional[ClusterCredentials] = Field(default=None)
    additional_kwargs: Optional[dict[str, Any]] = Field(default_factory=dict)


def generate_cluster_connection(cluster_config: ClusterConnectionConfig) -> Cluster:
    return Cluster(
        contact_points=cluster_config.contact_points, port=cluster_config.port,
        auth_provider=_get_auth_provider(cluster_config.credentials),
        **cluster_config.additional_kwargs
    )


def _get_auth_provider(credentials: Optional[ClusterCredentials] = None) -> PlainTextAuthProvider | None:
    return PlainTextAuthProvider(**credentials.model_dump()) if credentials else None
