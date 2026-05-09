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

    When the driver's load-balancer routes the two queries to different
    coordinators, ``system.peers_v2`` from coordinator B will include
    coordinator A, while ``system.local`` (routed to A) also returns A —
    producing a duplicate.  We dedup by host_id during construction.

    The back-fill loop below handles the inverse case: a node absent from
    both CQL results gets appended from driver metadata.
    """
    local_rows = list(session.execute("SELECT * FROM system.local"))
    seen_ids = {str(row.host_id) for row in local_rows}
    peers_rows = [
        r
        for r in session.execute("SELECT * FROM system.peers_v2")
        if str(r.host_id) not in seen_ids
    ]
    nodes = [NodeInfo(**row._asdict()) for row in local_rows + peers_rows]

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
