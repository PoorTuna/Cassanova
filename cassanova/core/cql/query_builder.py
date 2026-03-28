from json import loads
from logging import getLogger
from typing import Any

from cassanova.core.cql.sanitize_input import sanitize_identifier

logger = getLogger(__name__)

_ALLOWED_OPERATORS = frozenset({
    '=', '!=', '<', '>', '<=', '>=',
    'IN', 'LIKE', 'CONTAINS', 'CONTAINS KEY',
})


def build_where_clause(filter_json: str = None) -> str:
    if not filter_json:
        return ""

    filters = loads(filter_json)
    conditions = []
    for f in filters:
        col = f.get('col')
        op = f.get('op', '=')
        val = f.get('val', '')

        sanitize_identifier(col)
        _validate_operator(op)

        cql_val = _format_cql_value(val, op)
        conditions.append(f'"{col}" {op} {cql_val}')

    return " WHERE " + " AND ".join(conditions) if conditions else ""


def _validate_operator(op: str) -> None:
    if op.upper() not in _ALLOWED_OPERATORS:
        raise ValueError(f"Invalid CQL operator: {op}")


def _escape_cql_string(val: str) -> str:
    return val.replace("'", "''")


def _format_cql_value(val: Any, op: str) -> str:
    if isinstance(val, str) and val.lower() in ('true', 'false'):
        return val.lower()

    if isinstance(val, str) and (val.replace('.', '', 1).isdigit() or (
            val.startswith('-') and val[1:].replace('.', '', 1).isdigit())):
        return val

    if op.upper() == 'IN':
        items = [i.strip() for i in val.split(',')]
        formatted_items = []
        for item in items:
            if item.replace('.', '', 1).isdigit() or (
                    item.startswith('-') and item[1:].replace('.', '', 1).isdigit()):
                formatted_items.append(item)
            else:
                formatted_items.append(f"'{_escape_cql_string(item)}'")
        return f"({', '.join(formatted_items)})"

    if op.upper() == 'LIKE':
        search_term = val
        if '%' not in search_term:
            search_term = f"%{search_term}%"
        return f"'{_escape_cql_string(search_term)}'"

    return f"'{_escape_cql_string(val)}'"


def build_insert_query(keyspace: str, table: str, columns: list[str]) -> str:
    placeholders = ", ".join(["%s"] * len(columns))
    cols_clause = ", ".join([f'"{c}"' for c in columns])
    return f'INSERT INTO "{keyspace}"."{table}" ({cols_clause}) VALUES ({placeholders})'
