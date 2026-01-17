from typing import Any

from cassandra import ConsistencyLevel
from cassandra.cluster import Session
from cassandra.query import SimpleStatement

from cassanova.core.cql.sanitize_input import sanitize_identifier


def show_table_schema_cql(session: Session, keyspace: str, table: str,
                          cl: ConsistencyLevel = ConsistencyLevel.QUORUM) -> list[dict[str, Any]]:
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    statement = SimpleStatement(
        f"SELECT * FROM system_schema.columns WHERE keyspace_name = '{keyspace}'  AND table_name = '{table}';",
        consistency_level=cl)
    return [
        row._asdict() for row in session.execute(statement)
    ]


def show_table_description_cql(session: Session, keyspace: str, table: str,
                               cl: ConsistencyLevel = ConsistencyLevel.QUORUM) -> list[dict[str, Any]]:
    keyspace = sanitize_identifier(keyspace)
    table = sanitize_identifier(table)

    try:
        statement = SimpleStatement(f'DESCRIBE TABLE "{keyspace}"."{table}";',
                                    consistency_level=cl, keyspace=keyspace)
        result = [row._asdict() for row in session.execute(statement)]
        
        if result:
            return result
    except Exception:
        pass
    
    return show_table_schema_cql(session, keyspace, table, cl)
