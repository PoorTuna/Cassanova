from cassandra.cluster import Cluster, Session

from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.nodes import generate_nodes_info
from cassanova.core.metrics.get_dc_rack_distribution import get_dc_rack_distribution
from cassanova.core.metrics.get_description import get_cluster_description, get_cluster_version
from cassanova.core.metrics.get_health import get_cluster_health
from cassanova.core.metrics.get_technology_type import detect_database_technology
from cassanova.models.cluster import ClusterInfo
from cassanova.models.cluster_metrics import ClusterMetrics


def generate_cluster_info(cluster: Cluster, session: Session) -> ClusterInfo:
    return ClusterInfo(
        metrics=generate_cluster_metrics(cluster, session),
        nodes=generate_nodes_info(session),
        keyspaces=generate_keyspaces_info(list(cluster.metadata.keyspaces.items())),
    )


def generate_cluster_metrics(cluster: Cluster, session: Session) -> ClusterMetrics:
    return ClusterMetrics(
        **get_cluster_description(session),  # type: ignore[arg-type]
        **get_cluster_version(cluster),  # type: ignore[arg-type]
        **get_dc_rack_distribution(cluster),  # type: ignore[arg-type]
        **get_cluster_health(cluster, session),  # type: ignore[arg-type]
        technology=detect_database_technology(session),  # type: ignore[arg-type]
    )
