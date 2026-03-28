from typing import Literal

from cassandra.cluster import Session

_technology_cache: dict[str, str] = {}


def detect_database_technology(session: Session) -> Literal['scylla', 'dse', 'cassandra']:
    cluster_name = session.cluster.metadata.cluster_name or id(session.cluster)
    cached = _technology_cache.get(cluster_name)
    if cached:
        return cached

    result = _detect_technology(session)
    _technology_cache[cluster_name] = result
    return result


def _detect_technology(session: Session) -> Literal['scylla', 'dse', 'cassandra']:
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
