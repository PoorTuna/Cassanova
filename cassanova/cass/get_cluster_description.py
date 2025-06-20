from cassandra.cluster import Session


def get_cluster_description(cluster_session: Session) -> dict[str, str]:
    return {
        key: value for row in cluster_session.execute("DESCRIBE CLUSTER;")
        for key, value in row._asdict().items()
    }
