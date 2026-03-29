import json

import pytest

from cassanova.core.cql.query_builder import (
    _escape_cql_string,
    _format_cql_value,
    _validate_operator,
    build_insert_query,
    build_where_clause,
)


class TestBuildWhereClause:
    def test_none_filter_returns_empty(self):
        assert build_where_clause(None) == ""

    def test_empty_string_returns_empty(self):
        assert build_where_clause("") == ""

    def test_single_equality_filter(self):
        filters = json.dumps([{"col": "name", "op": "=", "val": "alice"}])
        result = build_where_clause(filters)
        assert result == """ WHERE "name" = 'alice'"""

    def test_multiple_filters(self):
        filters = json.dumps(
            [
                {"col": "age", "op": ">", "val": "25"},
                {"col": "city", "op": "=", "val": "NYC"},
            ]
        )
        result = build_where_clause(filters)
        assert '"age" > 25' in result
        assert "\"city\" = 'NYC'" in result
        assert " AND " in result

    def test_in_operator(self):
        filters = json.dumps([{"col": "status", "op": "IN", "val": "active,pending"}])
        result = build_where_clause(filters)
        assert "IN" in result
        assert "'active'" in result
        assert "'pending'" in result

    def test_like_operator(self):
        filters = json.dumps([{"col": "name", "op": "LIKE", "val": "ali"}])
        result = build_where_clause(filters)
        assert "LIKE" in result
        assert "%ali%" in result

    def test_boolean_value(self):
        filters = json.dumps([{"col": "active", "op": "=", "val": "true"}])
        result = build_where_clause(filters)
        assert "true" in result

    def test_numeric_value(self):
        filters = json.dumps([{"col": "age", "op": "=", "val": "30"}])
        result = build_where_clause(filters)
        assert "'30'" not in result
        assert "30" in result


class TestOperatorWhitelist:
    @pytest.mark.parametrize(
        "op",
        [
            "=",
            "!=",
            "<",
            ">",
            "<=",
            ">=",
            "IN",
            "LIKE",
            "CONTAINS",
            "CONTAINS KEY",
        ],
    )
    def test_valid_operators_pass(self, op):
        _validate_operator(op)

    @pytest.mark.parametrize(
        "op",
        [
            "= 1; DROP TABLE foo; --",
            "OR 1=1",
            "UNION SELECT",
            "; DROP",
            "= 1 OR",
            "",
            "BETWEEN",
        ],
    )
    def test_invalid_operators_rejected(self, op):
        with pytest.raises(ValueError, match="Invalid CQL operator"):
            _validate_operator(op)


class TestCqlInjectionPrevention:
    def test_operator_injection_rejected(self):
        filters = json.dumps([{"col": "name", "op": "= 1; DROP TABLE users; --", "val": "x"}])
        with pytest.raises(ValueError, match="Invalid CQL operator"):
            build_where_clause(filters)

    def test_column_injection_rejected(self):
        filters = json.dumps([{"col": "name; DROP TABLE users", "op": "=", "val": "x"}])
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            build_where_clause(filters)

    def test_value_single_quote_escaped(self):
        filters = json.dumps([{"col": "name", "op": "=", "val": "x'; DROP TABLE users; --"}])
        result = build_where_clause(filters)
        assert "x''; DROP TABLE users; --" in result
        assert "x'; DROP" not in result

    def test_in_value_single_quote_escaped(self):
        filters = json.dumps([{"col": "name", "op": "IN", "val": "a', b"}])
        result = build_where_clause(filters)
        assert "a''" in result

    def test_like_value_single_quote_escaped(self):
        filters = json.dumps([{"col": "name", "op": "LIKE", "val": "x'--"}])
        result = build_where_clause(filters)
        assert "x''--" in result

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError):
            build_where_clause("{invalid json")


class TestEscapeCqlString:
    def test_no_quotes(self):
        assert _escape_cql_string("hello") == "hello"

    def test_single_quote_doubled(self):
        assert _escape_cql_string("it's") == "it''s"

    def test_multiple_quotes(self):
        assert _escape_cql_string("a'b'c") == "a''b''c"


class TestFormatCqlValue:
    def test_boolean_true(self):
        assert _format_cql_value("true", "=") == "true"

    def test_boolean_false(self):
        assert _format_cql_value("false", "=") == "false"

    def test_integer(self):
        assert _format_cql_value("42", "=") == "42"

    def test_negative_number(self):
        assert _format_cql_value("-10", "=") == "-10"

    def test_float(self):
        assert _format_cql_value("3.14", "=") == "3.14"

    def test_string_value(self):
        assert _format_cql_value("hello", "=") == "'hello'"

    def test_in_operator_mixed(self):
        result = _format_cql_value("1,two,3", "IN")
        assert "1" in result
        assert "'two'" in result
        assert "3" in result

    def test_like_adds_wildcards(self):
        result = _format_cql_value("search", "LIKE")
        assert result == "'%search%'"

    def test_like_preserves_existing_wildcards(self):
        result = _format_cql_value("%search", "LIKE")
        assert result == "'%search'"


class TestBuildInsertQuery:
    def test_basic_insert(self):
        result = build_insert_query("my_ks", "my_table", ["id", "name"])
        assert result == 'INSERT INTO "my_ks"."my_table" ("id", "name") VALUES (%s, %s)'

    def test_single_column(self):
        result = build_insert_query("ks", "tbl", ["id"])
        assert result == 'INSERT INTO "ks"."tbl" ("id") VALUES (%s)'
