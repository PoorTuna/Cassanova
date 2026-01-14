from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, Session, SimpleStatement
from cassandra.cluster import Cluster, Session, SimpleStatement
from packaging.version import parse as parse_version


def get_cluster_description(cluster_session: Session, cl: ConsistencyLevel = ConsistencyLevel.QUORUM) -> dict[str, str]:
    statement = SimpleStatement(query_string="DESCRIBE CLUSTER;", consistency_level=cl)
    return {
        key: value for row in cluster_session.execute(statement)
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
