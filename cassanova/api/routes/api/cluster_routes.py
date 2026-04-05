from time import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from cassanova.api.dependencies.auth import require_permission
from cassanova.api.dependencies.db_session import get_session
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.nodes import generate_nodes_info
from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.cql.table_cleanup import drop_table_cql, truncate_table_cql
from cassanova.core.cql.table_info import show_table_description_cql, show_table_schema_cql
from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException
from cassanova.models.auth_models import WebUser

cluster_router = APIRouter()
clusters_config = get_clusters_config()

_schema_map_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _invalidate_schema_cache(cluster_name: str, session: Any = None) -> None:
    _schema_map_cache.pop(cluster_name, None)
    if session:
        session.cluster.refresh_schema_metadata()


@cluster_router.get("/cluster-keys")
def get_cluster_keys() -> list[str]:
    return list(clusters_config.clusters.keys())


@cluster_router.get("/clusters")
def get_clusters() -> list[dict[str, Any]]:
    return [get_cluster_safe(cluster_name) for cluster_name in clusters_config.clusters]


def get_cluster_safe(cluster_name: str) -> dict[str, Any]:
    try:
        session = get_session(cluster_name)
        cluster = session.cluster
        return generate_cluster_info(cluster, session).model_dump()
    except Exception:
        return {
            "name": cluster_name,
            "status": "Error connecting",
            "data_center": "Unknown",
            "rack": "Unknown",
            "release_version": "Unknown",
        }


@cluster_router.get("/cluster/{cluster_name}")
def get_cluster(cluster_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    cluster = session.cluster
    cluster_info = generate_cluster_info(cluster, session)
    return cluster_info.model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspaces")
def get_keyspaces(cluster_name: str) -> list[dict[str, Any]]:
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_list = list(cluster.metadata.keyspaces.items())
    return [keyspace.model_dump() for keyspace in generate_keyspaces_info(keyspace_list)]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def get_keyspace(cluster_name: str, keyspace_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace = cluster.metadata.keyspaces.get(keyspace_name)
    if not keyspace:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    return generate_keyspaces_info([(keyspace_name, keyspace)])[0].model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/cql")
def get_keyspace_cql(cluster_name: str, keyspace_name: str) -> dict[str, str]:
    session = get_session(cluster_name)
    ks_meta = session.cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    return {"cql": ks_meta.export_as_string()}


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/tables")
def get_tables(cluster_name: str, keyspace_name: str) -> list[dict[str, Any]]:
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")

    user_type_names = set(keyspace_metadata.user_types.keys())
    tables = [t for t in list(keyspace_metadata.tables.values()) if t.name not in user_type_names]

    return [table.model_dump() for table in generate_tables_info(tables)]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def get_table(cluster_name: str, keyspace_name: str, table_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_metadata = keyspace_metadata.tables.get(table_name)
    if table_metadata is None:
        raise HTTPException(status_code=404, detail="Table not found")

    if table_metadata.virtual:
        raise HTTPException(status_code=400, detail=f"{table_name} is a view, not a table")

    table_info = generate_tables_info([table_metadata])[0]
    return table_info.model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/cql")
def get_table_cql(cluster_name: str, keyspace_name: str, table_name: str) -> dict[str, str]:
    session = get_session(cluster_name)
    ks_meta = session.cluster.metadata.keyspaces.get(keyspace_name)
    if not ks_meta:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_meta = ks_meta.tables.get(table_name)
    if not table_meta:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"cql": table_meta.export_as_string()}


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/schema")
def get_table_schema(
    cluster_name: str, keyspace_name: str, table_name: str
) -> list[dict[str, Any]]:
    session = get_session(cluster_name)
    return show_table_schema_cql(session, keyspace_name, table_name)


@cluster_router.get(
    "/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/description"
)
def get_table_description(
    cluster_name: str, keyspace_name: str, table_name: str
) -> list[dict[str, Any]]:
    session = get_session(cluster_name)
    return show_table_description_cql(session, keyspace_name, table_name)


@cluster_router.get("/cluster/{cluster_name}/test")
def test_cluster_connection(cluster_name: str) -> dict[str, str]:
    try:
        session = get_session(cluster_name)
        session.execute("SELECT key FROM system.local LIMIT 1", timeout=5.0)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@cluster_router.get("/cluster/{cluster_name}/nodes")
def get_nodes(cluster_name: str) -> Any:
    session = get_session(cluster_name)
    try:
        return generate_nodes_info(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {e}") from e


@cluster_router.get("/cluster/{cluster_name}/settings")
def get_cluster_settings(cluster_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    try:
        rows = session.execute("SELECT * FROM system_views.settings")
        settings_dict = {row.name: row.value for row in rows}
    except Exception as e:
        error_message = str(e)
        if "Keyspace system_views does not exist" in error_message:
            raise SystemViewsUnavailableException(error_message) from e
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to query settings: {error_message}"
            ) from e

    return settings_dict


@cluster_router.get("/cluster/{cluster_name}/vnodes")
def get_cluster_vnodes(cluster_name: str) -> dict[str, list[dict[str, Any]]]:
    session = get_session(cluster_name)
    try:
        rows = list(
            session.execute("SELECT host_id, rpc_address, tokens FROM system.local")
        ) + list(session.execute("SELECT host_id, rpc_address, tokens FROM system.peers"))
        nodes = [
            {
                "host_id": str(row.host_id),
                "address": str(row.rpc_address),
                "tokens": [int(token) for token in row.tokens],
            }
            for row in rows
        ]

        # The two CQL queries above may hit different coordinators,
        # causing one node to be absent.  Back-fill from driver metadata.
        seen_ids = {n["host_id"] for n in nodes}
        for host in session.cluster.metadata.all_hosts():
            hid = str(host.host_id)
            if hid not in seen_ids:
                addr = str(host.broadcast_rpc_address) if getattr(host, "broadcast_rpc_address", None) else str(host.address)
                nodes.append(
                    {
                        "host_id": hid,
                        "address": addr,
                        "tokens": [int(t.value) for t in host.tokens] if host.tokens else [],
                    }
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster vnodes: {e}") from e

    return {"nodes": nodes}


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def delete_table(
    cluster_name: str,
    keyspace_name: str,
    table_name: str,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> JSONResponse:
    session = get_session(cluster_name)
    drop_table_cql(session, keyspace_name, table_name)
    _invalidate_schema_cache(cluster_name, session)
    return JSONResponse({"detail": f"Table {keyspace_name}.{table_name} deleted successfully"})


@cluster_router.delete(
    "/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/truncate"
)
def truncate_table(
    cluster_name: str,
    keyspace_name: str,
    table_name: str,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> dict[str, str]:
    session = get_session(cluster_name)
    truncate_table_cql(session, keyspace_name, table_name)
    return {"detail": f"Table {keyspace_name}.{table_name} truncated successfully"}


_SCHEMA_MAP_TTL_SECONDS = 60


@cluster_router.get("/cluster/{cluster_name}/schema-map")
def get_cluster_schema_map(cluster_name: str) -> dict[str, Any]:
    now = time()
    cached = _schema_map_cache.get(cluster_name)
    if cached and (now - cached[0]) < _SCHEMA_MAP_TTL_SECONDS:
        return cached[1]

    session = get_session(cluster_name)
    metadata = session.cluster.metadata

    schema_map = {}
    for ks_name, ks_meta in metadata.keyspaces.items():
        tables = {}
        for table_name, table_meta in ks_meta.tables.items():
            tables[table_name] = [col.name for col in table_meta.columns.values()]

        for view_name, view_meta in ks_meta.views.items():
            tables[view_name] = [col.name for col in view_meta.columns.values()]

        schema_map[ks_name] = tables

    _schema_map_cache[cluster_name] = (now, schema_map)
    return schema_map
