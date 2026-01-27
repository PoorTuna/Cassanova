from cassandra.metadata import KeyspaceMetadata

from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.constructors.serialize_to_primitive import serialize_to_primitive
from cassanova.models.keyspace import KeyspaceInfo


def generate_keyspaces_info(keyspaces: list[tuple[str, KeyspaceMetadata]]) -> list[KeyspaceInfo]:
    return [
        KeyspaceInfo(
            name=name,
            replication=keyspace_metadata.replication_strategy.export_for_schema() if keyspace_metadata.replication_strategy else None,
            virtual=keyspace_metadata.virtual,
            durable_writes=keyspace_metadata.durable_writes,
            tables=generate_tables_info(keyspace_metadata.tables.values()),
            indexes=[serialize_to_primitive(vars(v)) for v in keyspace_metadata.indexes.values()] ,
            user_types={k: serialize_to_primitive(v) for k, v in keyspace_metadata.user_types.items()},
            functions={k: serialize_to_primitive(v) for k, v in keyspace_metadata.functions.items()},
            aggregates={k: serialize_to_primitive(v) for k, v in keyspace_metadata.aggregates.items()},
            views={k: serialize_to_primitive(v) for k, v in keyspace_metadata.views.items()},
            graph_engine=keyspace_metadata.graph_engine,
        ) for name, keyspace_metadata in keyspaces
    ]
