from cassandra.cluster import Cluster


def get_dc_rack_distribution(cluster: Cluster) -> dict[str, int]:
    hosts = cluster.metadata.all_hosts()
    dc_count = len(set([host.datacenter for host in hosts]))
    rack_count = len(set([host.rack for host in hosts]))
    return {
        'dc_count': dc_count,
        'rack_count': rack_count
    }
