from collections import namedtuple
from unittest.mock import MagicMock

import pytest

from cassanova.core.cql.table_info import (
    show_table_schema_cql,
    show_table_description_cql,
)

SchemaRow = namedtuple("SchemaRow", ["keyspace_name", "table_name", "column_name", "type"])


class TestShowTableSchemaCql:
    def test_returns_schema_rows(self, mock_session):
        mock_session.execute.return_value = [
            SchemaRow("ks", "tbl", "id", "int"),
            SchemaRow("ks", "tbl", "name", "text"),
        ]
        result = show_table_schema_cql(mock_session, "ks", "tbl")
        assert len(result) == 2
        assert result[0]["column_name"] == "id"

    def test_rejects_invalid_keyspace(self, mock_session):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            show_table_schema_cql(mock_session, "bad; DROP", "tbl")

    def test_rejects_invalid_table(self, mock_session):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            show_table_schema_cql(mock_session, "ks", "bad table")


class TestShowTableDescriptionCql:
    def test_describe_success(self, mock_session):
        desc_row = namedtuple("DescRow", ["type", "name", "create_statement"])
        mock_session.execute.return_value = [
            desc_row("table", "tbl", "CREATE TABLE ks.tbl (...)")
        ]
        result = show_table_description_cql(mock_session, "ks", "tbl")
        assert len(result) == 1
        assert "create_statement" in result[0]

    def test_describe_failure_falls_back_to_schema(self, mock_session):
        schema_row = SchemaRow("ks", "tbl", "id", "int")

        mock_session.execute.side_effect = [
            Exception("DESCRIBE not supported"),
            [schema_row],
        ]

        result = show_table_description_cql(mock_session, "ks", "tbl")
        assert len(result) == 1
        assert result[0]["column_name"] == "id"
        assert mock_session.execute.call_count == 2
