from typing import Any

from cassandra.cluster import Session
from fastapi import HTTPException, APIRouter
from starlette.responses import JSONResponse

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection, ClusterConnectionConfig
from cassanova.consts.cass_tools import CassTools
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.nodes import generate_nodes_info
from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.cql.table_info import show_table_schema_cql, show_table_description_cql
from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException

clusters_config = get_clusters_config()
cassanova_api_getter_router = APIRouter()


@cassanova_api_getter_router.get("/clusters")
def get_clusters():
    return [get_cluster(cluster_name) for cluster_name in clusters_config.clusters.keys()]


@cassanova_api_getter_router.get("/cluster/{cluster_name}")
def get_cluster(cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    session: Session = cluster.connect()
    cluster_info = generate_cluster_info(cluster, session)
    return cluster_info.model_dump()


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspaces")
def get_keyspaces(cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspaces_info = [get_keyspace(cluster_name, keyspace_name) for keyspace_name in cluster.metadata.keyspaces.keys()]
    return keyspaces_info


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def get_keyspace(cluster_name: str, keyspace_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspace_info = generate_keyspaces_info([(keyspace_name, cluster.metadata.keyspaces.get(keyspace_name))])[0]
    return keyspace_info.model_dump()


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/tables")
def get_tables(cluster_name: str, keyspace_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    tables_metadata = keyspace_metadata.tables
    tables_info = [get_table(cluster_name, keyspace_name, table) for table in tables_metadata.keys()]
    return tables_info


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def get_table(cluster_name: str, keyspace_name: str, table_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_metadata = keyspace_metadata.tables.get(table_name)
    if table_metadata is None:
        raise HTTPException(status_code=404, detail="Table not found")
    table_info = generate_tables_info([table_metadata])[0]
    return table_info.model_dump()


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/schema")
def get_table_schema(cluster_name: str, keyspace_name: str, table_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    return show_table_schema_cql(session, keyspace_name, table_name)


@cassanova_api_getter_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/description")
def get_table_description(cluster_name: str, keyspace_name: str, table_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    return show_table_description_cql(session, keyspace_name, table_name)


@cassanova_api_getter_router.get("/tool/list")
def get_available_tools():
    return JSONResponse({'tools': CassTools.ALLOWED_TOOLS})


@cassanova_api_getter_router.get("/cluster/{cluster_name}/nodes")
def get_nodes(cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()
    try:
        return generate_nodes_info(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {e}")


@cassanova_api_getter_router.get("/cluster/{cluster_name}/settings")
def get_cluster_settings(cluster_name: str) -> dict[str, Any]:
    cluster_config = clusters_config.clusters.get(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

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


@cassanova_api_getter_router.get("/cluster/{cluster_name}/vnodes")
def get_cluster_vnodes(cluster_name: str) -> dict[str, list[dict[str, Any]]]:
    cluster_config = clusters_config.clusters.get(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    try:
        rows = list(session.execute("SELECT host_id, rpc_address, tokens FROM system.local")) + \
               list(session.execute("SELECT host_id, rpc_address, tokens FROM system.peers"))
        nodes = [
            {
                "host_id": str(row.host_id),
                "address": str(row.rpc_address),
                "tokens": [int(t) for t in row.tokens]
            }
            for row in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster vnodes: {e}")

    return {"nodes": nodes}
