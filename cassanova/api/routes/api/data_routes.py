from csv import DictReader, writer
from io import StringIO
from json import loads
from typing import Any

from cassandra.query import SimpleStatement
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from cassanova.api.dependencies.db_session import get_session
from cassanova.core.cql.converters import convert_value_for_cql
from cassanova.core.cql.query_builder import build_where_clause, build_insert_query

data_router = APIRouter()


@data_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/data")
def get_table_data(cluster_name: str, keyspace_name: str, table_name: str, limit: int = 100,
                   filter_json: str = None,
                   allow_filtering: bool = False, paging_state: str = None):
    session = get_session(cluster_name)

    where_clause = build_where_clause(filter_json)

    query = f"SELECT * FROM {keyspace_name}.{table_name}{where_clause}"
    if allow_filtering:
        query += " ALLOW FILTERING"

    try:
        statement = SimpleStatement(query, fetch_size=limit)

        actual_paging_state = None
        if paging_state and paging_state != "null":
            from binascii import unhexlify
            actual_paging_state = unhexlify(paging_state)

        rows = session.execute(statement, paging_state=actual_paging_state)

        from binascii import hexlify
        next_paging_state = hexlify(rows.paging_state).decode() if rows.paging_state else None

        result = {
            "rows": [dict(row._asdict()) for row in rows.current_rows],
            "next_paging_state": next_paging_state
        }
        return jsonable_encoder(result, custom_encoder={bytes: lambda var: var.hex()})
    except Exception as e:
        error_msg = str(e)
        if "ALLOW FILTERING" in error_msg:
            raise HTTPException(status_code=400,
                                detail="This query requires ALLOW FILTERING. Please enable it in the filter settings.")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {error_msg}")


@data_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/cell-metadata")
def get_cell_metadata(cluster_name: str, keyspace_name: str, table_name: str, pk: str, column: str):
    session = get_session(cluster_name)
    try:
        pk_data = loads(pk)
        where_clause = " AND ".join([f"{col} = %s" for col in pk_data.keys()])
        values = list(pk_data.values())

        query = f"SELECT TTL({column}), WRITETIME({column}) FROM {keyspace_name}.{table_name} WHERE {where_clause}"
        rows = list(session.execute(query, values))

        if not rows:
            return {"ttl": None, "writetime": None}

        row = rows[0]
        return {
            "ttl": row[0],
            "writetime": row[1]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cell metadata: {e}")


@data_router.put("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
def update_table_row(cluster_name: str, keyspace_name: str, table_name: str, update_data: dict[str, Any]):
    session = get_session(cluster_name)
    pk_data = update_data.get("pk", {})
    updates = update_data.get("updates", {})

    if not pk_data or not updates:
        raise HTTPException(status_code=400, detail="Missing PK or update data")

    set_clause = ", ".join([f"{col} = %s" for col in updates.keys()])
    where_clause = " AND ".join([f"{col} = %s" for col in pk_data.keys()])

    values = list(updates.values()) + list(pk_data.values())
    query = f"UPDATE {keyspace_name}.{table_name} SET {set_clause} WHERE {where_clause}"

    try:
        session.execute(query, values)
        return {"detail": "Row updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update row: {e}")


@data_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
def delete_table_row(cluster_name: str, keyspace_name: str, table_name: str, pk_data: dict[str, Any]):
    session = get_session(cluster_name)
    if not pk_data:
        raise HTTPException(status_code=400, detail="Missing PK data for deletion")

    where_clause = " AND ".join([f"{col} = %s" for col in pk_data.keys()])
    values = list(pk_data.values())
    query = f"DELETE FROM {keyspace_name}.{table_name} WHERE {where_clause}"

    try:
        session.execute(query, values)
        return {"detail": "Row deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete row: {e}")


@data_router.post("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
def insert_table_row(cluster_name: str, keyspace_name: str, table_name: str, row_data: dict[str, Any]):
    session = get_session(cluster_name)
    if not row_data:
        raise HTTPException(status_code=400, detail="Missing row data for insertion")

    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if not keyspace_metadata:
        raise HTTPException(status_code=404, detail="Keyspace not found")

    table_metadata = keyspace_metadata.tables.get(table_name)
    if not table_metadata:
        raise HTTPException(status_code=404, detail="Table not found")

    converted_values = []
    columns = []

    for col_name, value in row_data.items():
        columns.append(col_name)
        col_meta = table_metadata.columns.get(col_name)
        if not col_meta:
            raise HTTPException(status_code=400, detail=f"Unknown column: {col_name}")

        try:
            converted_values.append(convert_value_for_cql(value, str(col_meta.cql_type)))
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value '{value}' for column '{col_name}': {e}"
            )

    query = build_insert_query(keyspace_name, table_name, columns)

    try:
        session.execute(query, converted_values)
        return {"detail": "Row inserted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert row: {e}")


@data_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/export")
def export_table_data(cluster_name: str, keyspace_name: str, table_name: str,
                      filter_json: str = None, allow_filtering: bool = False):
    session = get_session(cluster_name)

    where_clause = build_where_clause(filter_json)
    query = f"SELECT * FROM {keyspace_name}.{table_name}{where_clause}"

    if allow_filtering:
        query += " ALLOW FILTERING"

    def generate_csv():
        rows = session.execute(query)
        output = StringIO()
        csv_writer = writer(output)
        headers = rows.column_names
        csv_writer.writerow(headers)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)
        for row in rows:
            clean_row = []
            for h in headers:
                val = getattr(row, h)
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                clean_row.append(val)
            csv_writer.writerow(clean_row)
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}_export.csv"}
    )


@data_router.post("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/import")
def import_table_data(cluster_name: str, keyspace_name: str, table_name: str, file: UploadFile = File(...)):
    session = get_session(cluster_name)

    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if not keyspace_metadata:
        raise HTTPException(status_code=404, detail="Keyspace not found")

    table_metadata = keyspace_metadata.tables.get(table_name)
    if not table_metadata:
        raise HTTPException(status_code=404, detail="Table not found")

    content = file.file.read()
    decoded = content.decode('utf-8')
    reader = DictReader(StringIO(decoded))
    success_count = 0
    errors = []

    for row in reader:
        try:
            converted_values = []
            columns = []

            for col_name, value in row.items():
                if not col_name:
                    continue

                columns.append(col_name)
                col_meta = table_metadata.columns.get(col_name)
                if not col_meta:
                    raise ValueError(f"Unknown column: {col_name}")

                converted_values.append(convert_value_for_cql(value, str(col_meta.cql_type)))

            query = build_insert_query(keyspace_name, table_name, columns)
            session.execute(query, converted_values)
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
