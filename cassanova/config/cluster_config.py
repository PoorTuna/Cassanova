from typing import Any

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.policies import (
    DCAwareRoundRobinPolicy,
    RetryPolicy,
    TokenAwarePolicy,
)
from pydantic import BaseModel, Field


class ClusterCredentials(BaseModel):
    username: str
    password: str


class ClusterConnectionConfig(BaseModel):
    contact_points: list[str]
    port: int = Field(default=9042)
    credentials: ClusterCredentials | None = Field(default=None)
    jmx_credentials: ClusterCredentials | None = Field(default=None)
    local_dc: str | None = Field(default=None)
    protocol_version: int | None = Field(default=None)
    additional_kwargs: dict[str, Any] | None = Field(default_factory=dict)


def generate_cluster_connection(cluster_config: ClusterConnectionConfig) -> Cluster:
    kwargs = dict(cluster_config.additional_kwargs or {})

    if cluster_config.local_dc:
        kwargs.setdefault(
            "load_balancing_policy",
            TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=cluster_config.local_dc)),
        )

    kwargs.setdefault("default_retry_policy", RetryPolicy())

    if cluster_config.protocol_version:
        kwargs["protocol_version"] = cluster_config.protocol_version

    return Cluster(
        contact_points=cluster_config.contact_points,
        port=cluster_config.port,
        auth_provider=_get_auth_provider(cluster_config.credentials),
        **kwargs,
    )


def _get_auth_provider(
    credentials: ClusterCredentials | None = None,
) -> PlainTextAuthProvider | None:
    return PlainTextAuthProvider(**credentials.model_dump()) if credentials else None
