from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import ClusterConnectionConfig
from cassanova.config.cluster_metadata import ClusterMetadata

admin_router = APIRouter(prefix="/admin", tags=["Admin"])


class CredentialsView(BaseModel):
    username: str
    password: str


class AdminClusterView(BaseModel):
    name: str
    source: str
    context: str | None
    contact_points: list[str]
    port: int
    credentials: CredentialsView | None
    jmx_credentials: CredentialsView | None
    has_credentials: bool
    has_jmx_credentials: bool
    has_additional_kwargs: bool
    last_seen: datetime | None
    miss_count: int


def _build_cluster_view(
    name: str,
    cc: ClusterConnectionConfig,
    meta: ClusterMetadata,
    expose_credentials: bool,
) -> AdminClusterView:
    return AdminClusterView(
        name=name,
        source=meta.source,
        context=meta.context,
        contact_points=cc.contact_points,
        port=cc.port,
        credentials=(
            CredentialsView(
                username=cc.credentials.username,
                password=cc.credentials.password,
            )
            if expose_credentials and cc.credentials
            else None
        ),
        jmx_credentials=(
            CredentialsView(
                username=cc.jmx_credentials.username,
                password=cc.jmx_credentials.password,
            )
            if expose_credentials and cc.jmx_credentials
            else None
        ),
        has_credentials=cc.credentials is not None,
        has_jmx_credentials=cc.jmx_credentials is not None,
        has_additional_kwargs=bool(cc.additional_kwargs),
        last_seen=meta.last_seen,
        miss_count=meta.miss_count,
    )


@admin_router.get("/config/clusters", response_model=list[AdminClusterView])
def list_all_clusters(
    expose_credentials: bool = Query(default=True),
) -> list[AdminClusterView]:
    cfg = get_clusters_config()
    return [
        _build_cluster_view(
            name,
            cc,
            cfg.cluster_metadata.get(name) or ClusterMetadata(),
            expose_credentials,
        )
        for name, cc in cfg.clusters.items()
    ]
