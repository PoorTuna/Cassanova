from cassandra.cluster import Cluster


def get_cluster_health(cluster: Cluster):
    hosts = cluster.metadata.all_hosts()
    total = len(hosts)
    up = sum(1 for host in hosts if host.is_up)
    down = total - up

    status = "Healthy" if down == 0 else "Degraded" if down < total else "Down"
    return {
        "total_nodes": total,
        "up_nodes": up,
        "down_nodes": down,
        "status": status
    }
