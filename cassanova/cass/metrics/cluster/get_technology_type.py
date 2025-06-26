from typing import Literal

from cassandra.cluster import Session


def detect_database_technology(session: Session) -> Literal['scylla', 'dse', 'cassandra']:
    try:
        session.execute("SELECT * FROM system.scylla_local LIMIT 1")
        return 'scylla'
    except Exception:
        pass

    try:
        row = session.execute("SELECT dse_version FROM system.local").one()
        if row and getattr(row, 'dse_version', None):
            return 'dse'
    except Exception:
        pass

    return 'cassandra'
