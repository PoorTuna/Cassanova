from cassandra.cluster import Cluster, Session
from pkg_resources import parse_version


def get_cluster_description(cluster_session: Session) -> dict[str, str]:
    return {
        key: value for row in cluster_session.execute("DESCRIBE CLUSTER;")
        for key, value in row._asdict().items()
    }


def get_cluster_version(cluster: Cluster) -> dict[str, str | bool] | None:
    versions = {
        host.release_version
        for host in cluster.metadata.all_hosts()
        if host.release_version is not None
    }
    if not versions:
        return None
    parsed_versions = [parse_version(version) for version in versions]
    return {
        'version': str(min(parsed_versions)),
        'is_fully_upgraded': len(versions) == 1
    }
