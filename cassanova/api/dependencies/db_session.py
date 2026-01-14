from cassandra.cluster import Session
from fastapi import HTTPException

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import generate_cluster_connection

clusters_config = get_clusters_config()


def get_session(cluster_name: str) -> Session:
    cluster_config = clusters_config.clusters.get(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    return cluster.connect()
