from __future__ import annotations

import json
from collections.abc import Generator
from csv import DictReader, writer
from io import StringIO
from logging import getLogger
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cassanova.models.auth_models import WebUser

from cassandra.cluster import Session
from cassandra.metadata import TableMetadata
from cassandra.query import BatchStatement, BatchType, SimpleStatement

from cassanova.core.cql.converters import convert_value_for_cql
from cassanova.core.cql.query_builder import build_insert_query

logger = getLogger(__name__)

_BATCH_SIZE = 50


def generate_csv_stream(session: Session, query: str) -> Generator[str, None, None]:
    rows = session.execute(query)
    output, csv_writer = _init_csv_writer()

    headers = rows.column_names
    yield _write_row(output, csv_writer, headers)

    for row in rows:
        clean_values = _extract_clean_values(row, headers)
        yield _write_row(output, csv_writer, clean_values)


def generate_json_stream(session: Session, query: str) -> Generator[str, None, None]:
    rows = session.execute(query)
    headers = rows.column_names
    for row in rows:
        clean_values = _extract_clean_values(row, headers)
        yield json.dumps(dict(zip(headers, clean_values)), default=str) + "\n"


def load_csv_data(
    content: bytes,
    keyspace_name: str,
    table_name: str,
    table_metadata: TableMetadata,
    session: Session,
    cluster_name: str = "",
    user: "WebUser | None" = None,
) -> dict[str, Any]:
    from cassanova.config.cassanova_config import get_clusters_config
    from cassanova.core.cql._executor import execute_cql

    batch_timeout = get_clusters_config().timeouts.batch
    reader = _create_csv_reader(content)
    success_count = 0
    errors = []

    batch = BatchStatement(batch_type=BatchType.UNLOGGED)
    batch_rows = 0
    insert_query = None

    for row in reader:
        try:
            columns, values = _prepare_insert_data(row, table_metadata)
            if insert_query is None:
                insert_query = build_insert_query(keyspace_name, table_name, columns)

            batch.add(SimpleStatement(insert_query), values)
            batch_rows += 1

            if batch_rows >= _BATCH_SIZE:
                execute_cql(session, batch, cluster_name, user, timeout=batch_timeout)
                success_count += batch_rows
                batch = BatchStatement(batch_type=BatchType.UNLOGGED)
                batch_rows = 0

        except Exception as e:
            if batch_rows > 0:
                try:
                    execute_cql(session, batch, cluster_name, user, timeout=batch_timeout)
                    success_count += batch_rows
                except Exception as batch_err:
                    errors.append(str(batch_err))
                batch = BatchStatement(batch_type=BatchType.UNLOGGED)
                batch_rows = 0
            errors.append(str(e))
            if len(errors) > 50:
                break

    if batch_rows > 0:
        try:
            execute_cql(session, batch, cluster_name, user, timeout=batch_timeout)
            success_count += batch_rows
        except Exception as e:
            errors.append(str(e))

    return {"success": success_count, "failed": len(errors), "errors": errors[:10]}


def _init_csv_writer() -> tuple[StringIO, Any]:
    output = StringIO()
    csv_writer = writer(output)
    return output, csv_writer


def _write_row(output: StringIO, csv_writer: Any, row_data: list[Any]) -> str:
    csv_writer.writerow(row_data)
    value = output.getvalue()
    output.truncate(0)
    output.seek(0)
    return value


def _extract_clean_values(row: Any, headers: list[str]) -> list[Any]:
    clean_row = []
    for h in headers:
        val = getattr(row, h)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        clean_row.append(val)
    return clean_row


def _create_csv_reader(content: bytes) -> DictReader:
    decoded = content.decode("utf-8")
    return DictReader(StringIO(decoded))


def _prepare_insert_data(row: dict, meta: TableMetadata) -> tuple[list[str], list[Any]]:
    columns = []
    values = []

    for col_name, value in row.items():
        if not col_name:
            continue

        col_meta = meta.columns.get(col_name)
        if not col_meta:
            raise ValueError(f"Unknown column: {col_name}")

        columns.append(col_name)
        values.append(convert_value_for_cql(value, str(col_meta.cql_type)))

    return columns, values
