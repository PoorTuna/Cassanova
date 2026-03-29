from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from starlette.responses import Response

from cassanova.api.dependencies.db_session import get_session
from cassanova.api.routes.api.cluster_routes import (
    get_cluster_settings,
    get_cluster_vnodes,
    get_nodes,
)
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.web.template_config import templates

clusters_config = get_clusters_config()
cassanova_ui_dashboard_router = APIRouter(tags=["UI"])


@cassanova_ui_dashboard_router.get("/")
def index(request: Request) -> Response:
    return templates.TemplateResponse(
        "index.html", {"request": request, "clusters": clusters_config.clusters}
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}")
def cluster_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    cluster_info = generate_cluster_info(cluster, session)
    return templates.TemplateResponse(
        "cluster.html",
        {
            "request": request,
            "cluster": cluster_info,
            "cluster_config_entry": cluster_name,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def keyspace_dashboard(request: Request, cluster_name: str, keyspace_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    ks_meta = cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    keyspace_info = generate_keyspaces_info([(keyspace_name, ks_meta)])[0]

    return templates.TemplateResponse(
        "keyspace.html",
        {
            "request": request,
            "keyspace": keyspace_info,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/nodes")
def nodes_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    nodes_info = get_nodes(cluster_name)

    return templates.TemplateResponse(
        "nodes.html",
        {
            "request": request,
            "nodes": nodes_info,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/settings")
def cluster_settings_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster

    settings_dict = get_cluster_settings(cluster_name)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "cluster_settings": settings_dict,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/vnodes")
def vnodes_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster

    vnodes = get_cluster_vnodes(cluster_name).get("nodes")
    return templates.TemplateResponse(
        "vnodes.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "vnodes": vnodes,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/users")
def users_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
        },
    )


@cassanova_ui_dashboard_router.get(
    "/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/explore"
)
def table_explorer_dashboard(
    request: Request, cluster_name: str, keyspace_name: str, table_name: str
) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    ks_meta = cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_metadata = ks_meta.tables.get(table_name)
    if not table_metadata:
        raise HTTPException(status_code=404, detail="Table not found")

    return templates.TemplateResponse(
        "explorer.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "keyspace_name": keyspace_name,
            "table_name": table_name,
            "primary_key": [col.name for col in table_metadata.primary_key],
            "columns": list(table_metadata.columns.keys()),
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/builder/keyspace")
def keyspace_builder_dashboard(request: Request, cluster_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    return templates.TemplateResponse(
        "keyspace-builder.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/builder/table")
def table_builder_dashboard(request: Request, cluster_name: str, keyspace_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    return templates.TemplateResponse(
        "table-builder.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "keyspace_name": keyspace_name,
        },
    )


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/builder")
def keyspace_editor_dashboard(request: Request, cluster_name: str, keyspace_name: str) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    ks_meta = cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")

    rs = ks_meta.replication_strategy
    strategy_class = rs.name if rs else "SimpleStrategy"

    replication = {}
    replication_factor = 3
    if strategy_class == "NetworkTopologyStrategy" and hasattr(rs, "dc_replication_factors"):
        replication = {dc: int(rf) for dc, rf in rs.dc_replication_factors.items()}
    elif strategy_class == "SimpleStrategy" and hasattr(rs, "replication_factor_info"):
        replication_factor = rs.replication_factor_info.all_replicas

    existing_keyspace = {
        "name": keyspace_name,
        "strategy_class": strategy_class,
        "replication": replication,
        "replication_factor": replication_factor,
        "durable_writes": ks_meta.durable_writes,
    }

    return templates.TemplateResponse(
        "keyspace-builder.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "keyspace_name": keyspace_name,
            "mode": "alter",
            "existing_keyspace": existing_keyspace,
        },
    )


@cassanova_ui_dashboard_router.get(
    "/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/builder"
)
def table_editor_dashboard(
    request: Request, cluster_name: str, keyspace_name: str, table_name: str
) -> Response:
    session = get_session(cluster_name)
    cluster = session.cluster
    ks_meta = cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_meta = ks_meta.tables.get(table_name)
    if not table_meta:
        raise HTTPException(status_code=404, detail="Table not found")

    pk_names = {col.name for col in table_meta.partition_key}
    ck_names = {col.name for col in table_meta.clustering_key}

    columns = []
    for col_name, col_meta in table_meta.columns.items():
        ck_order = "ASC"
        if col_name in ck_names and hasattr(col_meta, "is_reversed") and col_meta.is_reversed:
            ck_order = "DESC"

        columns.append(
            {
                "name": col_name,
                "type": str(col_meta.cql_type),
                "isPK": col_name in pk_names,
                "isCK": col_name in ck_names,
                "ckOrder": ck_order,
                "isStatic": getattr(col_meta, "is_static", False),
            }
        )

    compaction_class = ""
    if table_meta.options and "compaction" in table_meta.options:
        compaction = table_meta.options["compaction"]
        compaction_class = compaction.get("class", "") if isinstance(compaction, dict) else ""

    existing_schema = {
        "columns": columns,
        "compaction": compaction_class,
        "default_ttl": table_meta.options.get("default_time_to_live", 0)
        if table_meta.options
        else 0,
    }

    return templates.TemplateResponse(
        "table-builder.html",
        {
            "request": request,
            "cluster_name": cluster.metadata.cluster_name,
            "cluster_config_entry": cluster_name,
            "keyspace_name": keyspace_name,
            "table_name": table_name,
            "mode": "alter",
            "existing_schema": existing_schema,
        },
    )
