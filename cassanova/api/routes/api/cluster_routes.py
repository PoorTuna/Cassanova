from binascii import unhexlify, hexlify
from csv import DictReader, writer
from io import StringIO
from json import loads
from typing import Any

from cassandra.query import SimpleStatement
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from cassanova.api.dependencies.db_session import get_session
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info
from cassanova.core.constructors.nodes import generate_nodes_info
from cassanova.core.constructors.tables import generate_tables_info
from cassanova.core.cql.table_cleanup import drop_table_cql, truncate_table_cql
from cassanova.core.cql.table_info import show_table_schema_cql, show_table_description_cql
from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException

cluster_router = APIRouter()
clusters_config = get_clusters_config()


@cluster_router.get("/clusters")
def get_clusters():
    return [get_cluster_safe(cluster_name) for cluster_name in clusters_config.clusters.keys()]


def get_cluster_safe(cluster_name: str):
    try:
        session = get_session(cluster_name)
        cluster = session.cluster
        return generate_cluster_info(cluster, session).model_dump()
    except Exception:
        return {"name": cluster_name, "status": "Error connecting", "data_center": "Unknown", "rack": "Unknown",
                "release_version": "Unknown"}


@cluster_router.get("/cluster/{cluster_name}")
def get_cluster(cluster_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    cluster_info = generate_cluster_info(cluster, session)
    return cluster_info.model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspaces")
def get_keyspaces(cluster_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_list = list(cluster.metadata.keyspaces.items())
    return [keyspace.model_dump() for keyspace in generate_keyspaces_info(keyspace_list)]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def get_keyspace(cluster_name: str, keyspace_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace = cluster.metadata.keyspaces.get(keyspace_name)
    if not keyspace:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    return generate_keyspaces_info([(keyspace_name, keyspace)])[0].model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/tables")
def get_tables(cluster_name: str, keyspace_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    return [table.model_dump() for table in generate_tables_info(list(keyspace_metadata.tables.values()))]


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def get_table(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    cluster = session.cluster
    keyspace_metadata = cluster.metadata.keyspaces.get(keyspace_name)
    if keyspace_metadata is None:
        raise HTTPException(status_code=404, detail="Keyspace not found")
    table_metadata = keyspace_metadata.tables.get(table_name)
    if table_metadata is None:
        raise HTTPException(status_code=404, detail="Table not found")
    table_info = generate_tables_info([table_metadata])[0]
    return table_info.model_dump()


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/schema")
def get_table_schema(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    return show_table_schema_cql(session, keyspace_name, table_name)


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/description")
def get_table_description(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    return show_table_description_cql(session, keyspace_name, table_name)


@cluster_router.get("/cluster/{cluster_name}/nodes")
def get_nodes(cluster_name: str):
    session = get_session(cluster_name)
    try:
        return generate_nodes_info(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {e}")


@cluster_router.get("/cluster/{cluster_name}/settings")
def get_cluster_settings(cluster_name: str) -> dict[str, Any]:
    session = get_session(cluster_name)
    try:
        rows = session.execute("SELECT * FROM system_views.settings")
        settings_dict = {row.name: row.value for row in rows}
    except Exception as e:
        error_message = str(e)
        if "Keyspace system_views does not exist" in error_message:
            raise SystemViewsUnavailableException(error_message)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to query settings: {error_message}")

    return settings_dict


@cluster_router.get("/cluster/{cluster_name}/vnodes")
def get_cluster_vnodes(cluster_name: str) -> dict[str, list[dict[str, Any]]]:
    session = get_session(cluster_name)
    try:
        rows = list(session.execute("SELECT host_id, rpc_address, tokens FROM system.local")) + \
               list(session.execute("SELECT host_id, rpc_address, tokens FROM system.peers"))
        nodes = [
            {
                "host_id": str(row.host_id),
                "address": str(row.rpc_address),
                "tokens": [int(token) for token in row.tokens]
            }
            for row in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster vnodes: {e}")

    return {"nodes": nodes}


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}")
def delete_table(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    drop_table_cql(session, keyspace_name, table_name)
    return JSONResponse({"detail": f"Table {keyspace_name}.{table_name} deleted successfully"})


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/truncate")
def truncate_table(cluster_name: str, keyspace_name: str, table_name: str):
    session = get_session(cluster_name)
    truncate_table_cql(session, keyspace_name, table_name)
    return {"detail": f"Table {keyspace_name}.{table_name} truncated successfully"}


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/data")
def get_table_data(cluster_name: str, keyspace_name: str, table_name: str, limit: int = 100,
                   filter_json: str = None,
                   allow_filtering: bool = False, paging_state: str = None):
    session = get_session(cluster_name)

    where_clause = ""
    conditions = []

    if filter_json:
        try:
            filters = loads(filter_json)
            for f in filters:
                col = f.get('col')
                op = f.get('op', '=')
                val = f.get('val', '')

                if isinstance(val, str) and val.lower() in ('true', 'false'):
                    cql_val = val.lower()
                elif isinstance(val, str) and (val.replace('.', '', 1).isdigit() or (
                        val.startswith('-') and val[1:].replace('.', '', 1).isdigit())):
                    cql_val = val
                elif op.upper() == 'IN':
                    items = [i.strip() for i in val.split(',')]
                    formatted_items = []
                    for item in items:
                        if item.replace('.', '', 1).isdigit() or (
                                item.startswith('-') and item[1:].replace('.', '', 1).isdigit()):
                            formatted_items.append(item)
                        else:
                            formatted_items.append(f"'{item}'")
                    cql_val = f"({', '.join(formatted_items)})"
                elif op.upper() == 'LIKE':
                    search_term = val
                    if '%' not in search_term:
                        search_term = f"%{search_term}%"
                    cql_val = f"'{search_term}'"
                else:
                    cql_val = f"'{val}'"

                conditions.append(f"{col} {op} {cql_val}")
        except Exception as e:
            pass

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    query = f"SELECT * FROM {keyspace_name}.{table_name}{where_clause}"
    if allow_filtering:
        query += " ALLOW FILTERING"

    try:
        statement = SimpleStatement(query, fetch_size=limit)

        actual_paging_state = None
        if paging_state and paging_state != "null":
            actual_paging_state = unhexlify(paging_state)

        rows = session.execute(statement, paging_state=actual_paging_state)

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


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/cell-metadata")
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


@cluster_router.put("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
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


@cluster_router.delete("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
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


@cluster_router.post("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/row")
def insert_table_row(cluster_name: str, keyspace_name: str, table_name: str, row_data: dict[str, Any]):
    session = get_session(cluster_name)
    if not row_data:
        raise HTTPException(status_code=400, detail="Missing row data for insertion")

    columns = list(row_data.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    cols_clause = ", ".join(columns)
    values = list(row_data.values())

    query = f"INSERT INTO {keyspace_name}.{table_name} ({cols_clause}) VALUES ({placeholders})"

    try:
        session.execute(query, values)
        return {"detail": "Row inserted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert row: {e}")


@cluster_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/export")
def export_table_data(cluster_name: str, keyspace_name: str, table_name: str,
                      filter_json: str = None, allow_filtering: bool = False):
    session = get_session(cluster_name)
    query = f"SELECT * FROM {keyspace_name}.{table_name}"
    if filter_json:
        filters = loads(filter_json)
        where_clauses = []
        for f in filters:
            col = f['col']
            op = f['op']
            val = f['val']
            if isinstance(val, str):
                val_str = f"'{val}'"
            else:
                val_str = str(val)
            where_clauses.append(f"{col} {op} {val_str}")

        query += " WHERE " + " AND ".join(where_clauses)

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
            csv_writer.writerow([getattr(row, h) for h in headers])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={table_name}_export.csv"}
    )


@cluster_router.post("/cluster/{cluster_name}/keyspace/{keyspace_name}/table/{table_name}/import")
def import_table_data(cluster_name: str, keyspace_name: str, table_name: str, file: UploadFile = File(...)):
    session = get_session(cluster_name)
    content = file.file.read()
    decoded = content.decode('utf-8')
    reader = DictReader(StringIO(decoded))
    success_count = 0
    errors = []
    for row in reader:
        try:
            cols = ", ".join(row.keys())
            vals_list = []
            for v in row.values():
                if v is None or v == '':
                    vals_list.append("NULL")
                else:
                    vals_list.append(f"'{v}'" if not v.replace('.', '', 1).isdigit() else v)
            vals = ", ".join(vals_list)
            query = f"INSERT INTO {keyspace_name}.{table_name} ({cols}) VALUES ({vals})"
            session.execute(query)
            success_count += 1
        except Exception as e:
            errors.append(str(e))
            if len(errors) > 50: break

    return {
        "success": success_count,
        "failed": len(errors),
        "errors": errors[:10]
    }
