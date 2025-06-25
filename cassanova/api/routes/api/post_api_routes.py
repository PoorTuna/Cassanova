from json import dumps

from fastapi import HTTPException, APIRouter

from cassanova.cass.cql.execute_query import execute_query_cql
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection, ClusterConnectionConfig
from cassanova.models.cql_query import CQLQuery

clusters_config = get_clusters_config()
cassanova_api_post_router = APIRouter()


@cassanova_api_post_router.post("/cluster/{cluster_name}/operations/cqlsh")
def delete_table(cluster_name: str, query: CQLQuery):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()
    result = execute_query_cql(session, query)
    try:
        serialized_result = dumps(result)
    except (UnicodeDecodeError, TypeError) as e:
        serialized_result = str(result)
    return serialized_result
