from cassandra.cluster import Session

from cassanova.models.node import NodeInfo


def generate_nodes_info(session: Session) -> list[NodeInfo]:
    rows = list(session.execute("SELECT * FROM system.local")) + list(
        session.execute("SELECT * FROM system.peers_v2")
    )
    return [NodeInfo(**row._asdict()) for row in rows]
