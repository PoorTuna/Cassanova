from cassandra.cluster import Session


def get_total_cluster_size_estimate(session: Session):
    total_bytes = 0

    rows = session.execute("SELECT mean_partition_size, partitions_count FROM system.size_estimates")

    for row in rows:
        if row.mean_partition_size and row.partitions_count:
            total_bytes += row.mean_partition_size * row.partitions_count

    return _format_bytes(total_bytes)

def _format_bytes(num_bytes):
    gb = num_bytes / (1024 ** 3)
    return f"{gb:.2f} GB"
