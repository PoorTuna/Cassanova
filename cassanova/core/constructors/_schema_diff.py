"""Compare the schemas of two Cassandra clusters."""

from typing import Any

from cassandra.metadata import KeyspaceMetadata

_SYSTEM_KEYSPACES = frozenset({
    "system", "system_schema", "system_auth", "system_distributed",
    "system_traces", "system_virtual_schema", "system_views",
    "dse_system", "dse_security", "dse_perf", "dse_leases",
    "dse_insights", "dse_insights_local", "dse_analytics",
    "solr_admin", "HiveMetaStore", "dsefs",
})


def compare_schemas(
    keyspaces_a: dict[str, KeyspaceMetadata],
    keyspaces_b: dict[str, KeyspaceMetadata],
) -> dict[str, Any]:
    user_a = {k: v for k, v in keyspaces_a.items() if k not in _SYSTEM_KEYSPACES}
    user_b = {k: v for k, v in keyspaces_b.items() if k not in _SYSTEM_KEYSPACES}

    all_ks = sorted(set(user_a) | set(user_b))
    result: dict[str, Any] = {}

    for ks_name in all_ks:
        if ks_name in user_a and ks_name not in user_b:
            result[ks_name] = {"status": "only_a"}
        elif ks_name not in user_a and ks_name in user_b:
            result[ks_name] = {"status": "only_b"}
        else:
            result[ks_name] = _compare_keyspace(user_a[ks_name], user_b[ks_name])

    return result


def _compare_keyspace(a: KeyspaceMetadata, b: KeyspaceMetadata) -> dict[str, Any]:
    rep_a = str(a.replication_strategy.export_for_schema()) if a.replication_strategy else ""
    rep_b = str(b.replication_strategy.export_for_schema()) if b.replication_strategy else ""

    tables_diff = _compare_tables(a.tables, b.tables)

    has_diff = rep_a != rep_b or any(
        t.get("status") != "identical" for t in tables_diff.values()
    )

    entry: dict[str, Any] = {
        "status": "different" if has_diff else "identical",
        "tables": tables_diff,
    }
    if rep_a != rep_b:
        entry["replication_a"] = rep_a
        entry["replication_b"] = rep_b

    return entry


def _compare_tables(
    tables_a: dict[str, Any],
    tables_b: dict[str, Any],
) -> dict[str, Any]:
    all_tables = sorted(set(tables_a) | set(tables_b))
    result: dict[str, Any] = {}

    for name in all_tables:
        if name in tables_a and name not in tables_b:
            result[name] = {"status": "only_a"}
        elif name not in tables_a and name in tables_b:
            result[name] = {"status": "only_b"}
        else:
            result[name] = _compare_table(tables_a[name], tables_b[name])

    return result


def _compare_table(a: Any, b: Any) -> dict[str, Any]:
    pk_a = [c.name for c in a.partition_key]
    pk_b = [c.name for c in b.partition_key]
    ck_a = [c.name for c in a.clustering_key]
    ck_b = [c.name for c in b.clustering_key]

    columns_diff = _compare_columns(a.columns, b.columns)

    has_diff = pk_a != pk_b or ck_a != ck_b or any(
        c.get("status") != "identical" for c in columns_diff.values()
    )

    entry: dict[str, Any] = {
        "status": "different" if has_diff else "identical",
        "columns": columns_diff,
    }
    if pk_a != pk_b:
        entry["pk_a"] = pk_a
        entry["pk_b"] = pk_b
    if ck_a != ck_b:
        entry["ck_a"] = ck_a
        entry["ck_b"] = ck_b

    return entry


def _compare_columns(cols_a: dict[str, Any], cols_b: dict[str, Any]) -> dict[str, Any]:
    all_cols = sorted(set(cols_a) | set(cols_b))
    result: dict[str, Any] = {}

    for name in all_cols:
        if name in cols_a and name not in cols_b:
            result[name] = {"status": "only_a", "type_a": str(cols_a[name].cql_type)}
        elif name not in cols_a and name in cols_b:
            result[name] = {"status": "only_b", "type_b": str(cols_b[name].cql_type)}
        else:
            type_a = str(cols_a[name].cql_type)
            type_b = str(cols_b[name].cql_type)
            if type_a == type_b:
                result[name] = {"status": "identical", "type_a": type_a}
            else:
                result[name] = {"status": "different", "type_a": type_a, "type_b": type_b}

    return result
