from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from cassanova.api.dependencies.auth import require_permissions
from cassanova.api.dependencies.db_session import get_session
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.nodes import generate_nodes_info
from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.cql.table_cleanup import drop_table_cql, truncate_table_cql
from cassanova.core.cql.table_info import show_table_schema_cql, show_table_description_cql
from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException

cluster_router = APIRouter()
clusters_config = get_clusters_config()


@cluster_router.get("/clusters")
def get_clusters():
    return [get_cluster_safe(cluster_name) for cluster_name in clusters_config.clusters.keys()]


def get_cluster_safe(cluster_name: str):
    try:
        session = get_session(cluster_name)
        cluster = session.cluster
        return generate_cluster_info(cluster, session).model_dump()
    except Exception:
        return {"name": cluster_name, "status": "Error connecting", "data_center": "Unknown", "rack": "Unknown",
                "release_version": "Unknown"}


@cluster_router.get("/cluster/{cluster_name}")
def get_cluster(cluster_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    cluster_info = generate_cluster_info(cluster, session)
    return cluster_info.model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspaces")
def get_keyspaces(cluster_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_list = list(cluster.metadata.keyspaces.items())
    return [keyspace.model_dump() for keyspace in generate_keyspaces_info(keyspace_list)]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def get_keyspace(cluster_name: str, keyspace_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace = cluster.metadata.keyspaces.get(keyspace_name)
    if not keyspace:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    return generate_keyspaces_info([(keyspace_name, keyspace)])[0].model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/tables")
def get_tables(cluster_name: str, keyspace_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")

    user_type_names = set(keyspace_metadata.user_types.keys())
    tables = [t for t in list(keyspace_metadata.tables.values()) if t.name not in user_type_names]
    
    return [table.model_dump() for table in generate_tables_info(tables)]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def get_table(cluster_name: str, keyspace_name: str, table_name: str):
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


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/schema")
def get_table_schema(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    return show_table_schema_cql(session, keyspace_name, table_name)


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/description")
def get_table_description(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    return show_table_description_cql(session, keyspace_name, table_name)


@cluster_router.get("/cluster/{cluster_name}/nodes")
def get_nodes(cluster_name: str):
    session = get_session(cluster_name)
    try:
        return generate_nodes_info(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {e}")


@cluster_router.get("/cluster/{cluster_name}/settings")
def get_cluster_settings(cluster_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    try:
        rows = session.execute("SELECT * FROM system_views.settings")
        settings_dict = {row.name: row.value for row in rows}
    except Exception as e:
        error_message = str(e)
        if "Keyspace system_views does not exist" in error_message:
            raise SystemViewsUnavailableException(error_message)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to query settings: {error_message}")

    return settings_dict


@cluster_router.get("/cluster/{cluster_name}/vnodes")
def get_cluster_vnodes(cluster_name: str) -> dict[str, list[dict[str, Any]]]:
    session = get_session(cluster_name)
    try:
        rows = list(session.execute("SELECT host_id, rpc_address, tokens FROM system.local")) + \
               list(session.execute("SELECT host_id, rpc_address, tokens FROM system.peers"))
        nodes = [
            {
                "host_id": str(row.host_id),
                "address": str(row.rpc_address),
                "tokens": [int(token) for token in row.tokens]
            }
            for row in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster vnodes: {e}")

    return {"nodes": nodes}


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def delete_table(cluster_name: str, keyspace_name: str, table_name: str, _user=Depends(require_permissions("cluster:admin"))):
    session = get_session(cluster_name)
    drop_table_cql(session, keyspace_name, table_name)
    return JSONResponse({"detail": f"Table {keyspace_name}.{table_name} deleted successfully"})


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/truncate")
def truncate_table(cluster_name: str, keyspace_name: str, table_name: str, _user=Depends(require_permissions("cluster:admin"))):
    session = get_session(cluster_name)
    truncate_table_cql(session, keyspace_name, table_name)
    return {"detail": f"Table {keyspace_name}.{table_name} truncated successfully"}


@cluster_router.get("/cluster/{cluster_name}/schema-map")
def get_cluster_schema_map(cluster_name: str):
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

    return schema_map
