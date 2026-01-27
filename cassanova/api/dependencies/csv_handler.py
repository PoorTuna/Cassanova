from csv import DictReader, writer
from io import StringIO
from typing import Generator, Any

from cassandra.cluster import Session
from cassandra.metadata import TableMetadata

from cassanova.core.cql.converters import convert_value_for_cql
from cassanova.core.cql.query_builder import build_insert_query


def generate_csv_stream(session: Session, query: str) -> Generator[str, None, None]:
    rows = session.execute(query)
    output, csv_writer = _init_csv_writer()

    headers = rows.column_names
    yield _write_row(output, csv_writer, headers)

    for row in rows:
        clean_values = _extract_clean_values(row, headers)
        yield _write_row(output, csv_writer, clean_values)


def load_csv_data(content: bytes, keyspace_name: str, table_name: str, table_metadata: TableMetadata,
                  session: Session) -> dict[str, Any]:
    reader = _create_csv_reader(content)
    success_count = 0
    errors = []

    for row in reader:
        try:
            _insert_csv_row(row, keyspace_name, table_name, table_metadata, session)
            success_count += 1
        except Exception as e:
            errors.append(str(e))
            if len(errors) > 50:
                break

    return {
        "success": success_count,
        "failed": len(errors),
        "errors": errors[:10]
    }


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
        if hasattr(val, 'isoformat'):
            val = val.isoformat()
        clean_row.append(val)
    return clean_row


def _create_csv_reader(content: bytes) -> DictReader:
    decoded = content.decode('utf-8')
    return DictReader(StringIO(decoded))


def _insert_csv_row(row: dict, keyspace: str, table: str, meta: TableMetadata, session: Session):
    columns, values = _prepare_insert_data(row, meta)
    query = build_insert_query(keyspace, table, columns)
    session.execute(query, values)


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
