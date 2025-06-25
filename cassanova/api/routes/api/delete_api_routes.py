from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse

from cassanova.cass.cql.table_cleanup import drop_table_cql, truncate_table_cql
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection, ClusterConnectionConfig

clusters_config = get_clusters_config()
cassanova_api_deleter_router = APIRouter()


@cassanova_api_deleter_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def delete_table(cluster_name: str, keyspace_name: str, table_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    drop_table_cql(session, keyspace_name, table_name)

    return JSONResponse({"detail": f"Table {keyspace_name}.{table_name} deleted successfully"})


@cassanova_api_deleter_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/truncate")
def truncate_table(cluster_name: str, keyspace_name: str, table_name: str):
    # todo: get_cluster_config
    cluster_config = clusters_config.clusters.get(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    truncate_table_cql(session, keyspace_name, table_name)

    return {"detail": f"Table {keyspace_name}.{table_name} truncated successfully"}
