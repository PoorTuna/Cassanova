from cassandra.cluster import Session

from cassanova.models.node import NodeInfo


def host_tokens_from_metadata(session: Session, host) -> list[int]:
    """Tokens owned by ``host`` according to the driver's token map.

    The driver's ``Host`` object has no ``.tokens`` attribute; ownership
    lives centrally in ``cluster.metadata.token_map.token_to_host_owner``.
    Returns an empty list if the token map hasn't been built yet.
    """
    token_map = session.cluster.metadata.token_map
    if token_map is None:
        return []
    return [
        int(token.value)
        for token, owner in token_map.token_to_host_owner.items()
        if owner.host_id == host.host_id
    ]


def generate_nodes_info(session: Session) -> list[NodeInfo]:
    """Build a complete node list from CQL system tables.

    ``system.local`` and ``system.peers_v2`` may be routed to different
    coordinators by the driver's load-balancing policy (especially behind
    a load balancer).  ``system.peers_v2`` excludes its own coordinator,
    so a coordinator mismatch leaves one node absent from the union.

    We use the driver's discovered-host list as a safety net: any node
    the driver knows about but the CQL results missed gets appended with
    the subset of metadata the driver exposes.
    """
    rows = list(session.execute("SELECT * FROM system.local")) + list(
        session.execute("SELECT * FROM system.peers_v2")
    )
    nodes = [NodeInfo(**row._asdict()) for row in rows]

    seen_ids = {n.host_id for n in nodes}
    for host in session.cluster.metadata.all_hosts():
        host_id = str(host.host_id)
        if host_id in seen_ids:
            continue
        rpc_addr = getattr(host, "broadcast_rpc_address", None)
        nodes.append(
            NodeInfo(
                host_id=host_id,
                data_center=host.datacenter,
                rack=host.rack,
                release_version=host.release_version,
                tokens=host_tokens_from_metadata(session, host),
                broadcast_address=str(host.broadcast_address) if host.broadcast_address else None,
                listen_address=str(host.listen_address) if host.listen_address else None,
                rpc_address=str(rpc_addr) if rpc_addr else None,
            )
        )

    return nodes
