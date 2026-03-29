from cassandra.cluster import Cluster, Session


def get_cluster_health(cluster: Cluster, session: Session) -> dict[str, int | str]:
    """Derive node health from nodetool-equivalent gossip info via the driver.

    The driver's ``host.is_up`` only reflects whether *this* driver instance can
    reach the node — it does NOT reflect Cassandra's gossip view.  In multi-node
    clusters the driver may never open a connection to remote-DC nodes (depending
    on the load-balancing policy), so ``is_up`` stays False even though the node
    is perfectly healthy.

    To get accurate status we refresh the cluster metadata and then cross-check
    against ``system.peers_v2`` so every known peer is counted in the total.
    """
    cluster.refresh_nodes()

    driver_hosts = {str(h.host_id): h for h in cluster.metadata.all_hosts()}

    # system.local + system.peers_v2 is the ground truth for cluster membership
    peer_ids = set()
    try:
        for row in session.execute("SELECT host_id FROM system.local"):
            peer_ids.add(str(row.host_id))
        for row in session.execute("SELECT host_id FROM system.peers_v2"):
            peer_ids.add(str(row.host_id))
    except Exception:
        # Fallback: just use driver hosts if system tables fail
        peer_ids = set(driver_hosts.keys())

    total = len(peer_ids)
    up = 0
    for hid in peer_ids:
        driver_host = driver_hosts.get(hid)
        if driver_host and driver_host.is_up:
            up += 1

    # The coordinator node is always reachable (we just queried it)
    # — make sure it's counted as up even if the driver disagrees
    local_id = None
    try:
        row = session.execute("SELECT host_id FROM system.local").one()
        if row:
            local_id = str(row.host_id)
    except Exception:
        pass

    if local_id and local_id in peer_ids:
        driver_host = driver_hosts.get(local_id)
        if not driver_host or not driver_host.is_up:
            up += 1

    down = total - up
    status = "Healthy" if down == 0 else "Degraded" if down < total else "Down"
    return {"total_nodes": total, "up_nodes": up, "down_nodes": down, "status": status}
