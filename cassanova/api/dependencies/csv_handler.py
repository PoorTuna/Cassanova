from csv import DictReader, writer
from io import StringIO
from typing import Generator, Any

from cassandra.cluster import Session
from cassandra.metadata import TableMetadata

from cassanova.core.cql.converters import convert_value_for_cql
from cassanova.core.cql.query_builder import build_insert_query

def generate_csv_stream(session: Session, query: str) -> Generator[str, None, None]:
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

def load_csv_data(content: bytes, keyspace_name: str, table_name: str, table_metadata: TableMetadata, session: Session) -> dict[str, Any]:
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
