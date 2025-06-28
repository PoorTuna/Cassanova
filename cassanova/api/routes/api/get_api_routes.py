from cassandra.cluster import Session
from fastapi import HTTPException, APIRouter

from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.cql.table_info import show_table_schema_cql, show_table_description_cql
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection, ClusterConnectionConfig

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
