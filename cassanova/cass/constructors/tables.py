from typing import Any

from cassandra.metadata import TableMetadata

from cassanova.cass.constructors.serialize_to_primitive import serialize_to_primitive
from cassanova.models.cluster_info.table import TableInfo


def generate_tables_info(tables_metadata: list[TableMetadata]) -> list[TableInfo]:
    return [TableInfo(**serialize_to_primitive(_serialize_table_metadata(table_meta))) for table_meta in
            tables_metadata]


def _serialize_table_metadata(table: TableMetadata) -> dict[str, Any]:
    return {
        "name": table.name,
        "partition_key": [col.name for col in table.partition_key],
        "clustering_key": [col.name for col in table.clustering_key],
        "columns": {k: serialize_to_primitive(v) for k, v in table.columns.items()},
        "indexes": [serialize_to_primitive(vars(v)) for v in table.indexes.values()],
        "options": {k: str(v) for k, v in table.options.items()},
        "comparator": serialize_to_primitive(table.comparator),
        "triggers": dict(table.triggers),
        "views": {k: serialize_to_primitive(v) for k, v in table.views.items()},
        "virtual": table.virtual,
        "is_compact_storage": table.is_compact_storage,
        "extensions": serialize_to_primitive(table.extensions or {}),
    }
