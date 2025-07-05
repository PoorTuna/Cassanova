from cassandra import ConsistencyLevel
from cassandra.cluster import Session
from cassandra.query import SimpleStatement

from cassanova.core.cql.sanitize_input import sanitize_identifier


def drop_table_cql(session: Session, keyspace: str, table: str, cl: ConsistencyLevel = ConsistencyLevel.QUORUM):
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    statement = SimpleStatement(f"DROP TABLE IF EXISTS {table};",
                                consistency_level=cl, keyspace=keyspace)
    session.execute(statement)


def truncate_table_cql(session: Session,
                       keyspace: str, table: str, cl: ConsistencyLevel = ConsistencyLevel.QUORUM):
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    statement = SimpleStatement(f"TRUNCATE {table};",
                                consistency_level=cl, keyspace=keyspace)
    session.execute(statement)
