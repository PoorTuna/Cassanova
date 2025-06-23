from cassandra.metadata import KeyspaceMetadata

from cassanova.cass.constructors.tables import generate_tables_info
from cassanova.models.cluster_info import KeyspaceInfo


def generate_keyspaces_info(keyspaces: list[tuple[str, KeyspaceMetadata]]) -> list[KeyspaceInfo]:
    return [
        KeyspaceInfo(
            name=name,
            replication=keyspace_metadata.replication_strategy.export_for_schema() if keyspace_metadata.replication_strategy else None,
            virtual=keyspace_metadata.virtual,
            durable_writes=keyspace_metadata.durable_writes,
            tables=generate_tables_info(keyspace_metadata.tables.values())
        ) for name, keyspace_metadata in keyspaces
    ]
