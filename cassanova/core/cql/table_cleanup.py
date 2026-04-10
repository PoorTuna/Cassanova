from cassandra import ConsistencyLevel
from cassandra.cluster import Session
from cassandra.query import SimpleStatement

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.cql._executor import execute_cql
from cassanova.core.cql.sanitize_input import sanitize_identifier
from cassanova.models.auth_models import WebUser


def drop_table_cql(
    session: Session,
    keyspace: str,
    table: str,
    cluster_name: str,
    user: WebUser | None,
    cl: ConsistencyLevel = ConsistencyLevel.QUORUM,
) -> None:
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    statement = SimpleStatement(
        f"DROP TABLE IF EXISTS {table};", consistency_level=cl, keyspace=keyspace
    )
    execute_cql(
        session, statement, cluster_name, user,
        timeout=get_clusters_config().timeouts.ddl,
    )


def truncate_table_cql(
    session: Session,
    keyspace: str,
    table: str,
    cluster_name: str,
    user: WebUser | None,
    cl: ConsistencyLevel = ConsistencyLevel.QUORUM,
) -> None:
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    statement = SimpleStatement(f"TRUNCATE {table};", consistency_level=cl, keyspace=keyspace)
    execute_cql(
        session, statement, cluster_name, user,
        timeout=get_clusters_config().timeouts.ddl,
    )
