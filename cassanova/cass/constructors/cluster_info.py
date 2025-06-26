from cassandra.cluster import Session, Cluster

from cassanova.cass.constructors.keyspaces import generate_keyspaces_info
from cassanova.cass.constructors.nodes import generate_nodes_info
from cassanova.cass.metrics.cluster.get_description import get_cluster_description, get_cluster_version
from cassanova.cass.metrics.cluster.get_estimated_size import get_total_cluster_size_estimate
from cassanova.cass.metrics.cluster.get_health import get_cluster_health
from cassanova.cass.metrics.cluster.get_technology_type import detect_database_technology
from cassanova.cass.metrics.topology.get_dc_rack_distribution import get_dc_rack_distribution
from cassanova.models.cluster_info.cluster import ClusterInfo
from cassanova.models.cluster_metrics import ClusterMetrics


def generate_cluster_info(cluster: Cluster, session: Session) -> ClusterInfo:
    return ClusterInfo(
        metrics=generate_cluster_metrics(cluster, session),
        nodes=generate_nodes_info(),
        keyspaces=generate_keyspaces_info(list(cluster.metadata.keyspaces.items()))
    )


def generate_cluster_metrics(cluster: Cluster, session: Session) -> ClusterMetrics:
    return ClusterMetrics(
        **get_cluster_description(session),
        **get_cluster_version(cluster),
        **get_dc_rack_distribution(cluster),
        **get_cluster_health(cluster),
        technology=detect_database_technology(session),
        cluster_size=get_total_cluster_size_estimate(session),
    )
