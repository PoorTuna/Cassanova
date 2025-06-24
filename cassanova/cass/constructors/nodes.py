from cassanova.models.cluster_info.node import NodeInfo


def generate_nodes_info() -> list[NodeInfo]:
    return [
            NodeInfo(name="node1", status="Up", load="4.2 GB", cpu_percent=18.5, ram_percent=72.3, token_range="0 - 10000"),
        ]
