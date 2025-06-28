from cassandra import ConsistencyLevel
from cassandra.cluster import Session
from cassandra.query import SimpleStatement


def get_total_cluster_size_estimate(session: Session, cl: ConsistencyLevel = ConsistencyLevel.QUORUM) -> str | None:
    total_bytes = 0
    statement = SimpleStatement(query_string="SELECT mean_partition_size, partitions_count FROM system.size_estimates",
                                consistency_level=cl)
    rows = session.execute(statement)

    for row in rows:
        if row.mean_partition_size and row.partitions_count:
            total_bytes += row.mean_partition_size * row.partitions_count

    if not total_bytes:
        return None

    return _format_bytes(total_bytes)


def _format_bytes(num_bytes):
    gb = num_bytes / (1024 ** 3)
    return f"{gb:.2f} GB"
