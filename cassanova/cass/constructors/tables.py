from typing import Any

from cassandra.metadata import TableMetadata

from cassanova.models.cluster_info import TableInfo


def generate_tables_info(tables_metadata: list[TableMetadata]) -> list[TableInfo]:
    return [TableInfo(**_serialize_table_metadata(table_meta)) for table_meta in tables_metadata]

def _serialize_table_metadata(table_meta: TableMetadata) -> dict[str, Any]:
    return {key: _serialize_metadata_property(value) for key, value in vars(table_meta).items()}


def _serialize_metadata_property(obj: Any) -> Any:
    """
        Recursively serializes Cassandra driver metadata objects (e.g., TableMetadata, KeyspaceMetadata)
        into JSON-serializable dictionaries. Supports nested structures and Cassandra-specific types.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if hasattr(obj, 'as_cql_query'):
        return obj.as_cql_query()
    if hasattr(obj, 'export_for_schema'):
        return obj.export_for_schema()
    if hasattr(obj, '_asdict'):
        return {k: _serialize_metadata_property(v) for k, v in obj._asdict().items()}
    if isinstance(obj, dict):
        return {_serialize_metadata_property(k): _serialize_metadata_property(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_serialize_metadata_property(v) for v in obj]
    if hasattr(obj, '__dict__'):
        return {k: _serialize_metadata_property(v) for k, v in vars(obj).items() if not k.startswith('_')}
    return obj
