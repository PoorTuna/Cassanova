from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cassanova.api.dependencies.csv_handler import (
    _create_csv_reader,
    _init_csv_writer,
    _prepare_insert_data,
    _write_row,
    generate_csv_stream,
    load_csv_data,
)


def _make_column_meta(cql_type: str) -> MagicMock:
    col = MagicMock()
    col.cql_type = cql_type
    return col


def _make_table_metadata(columns_map: dict[str, str]) -> MagicMock:
    meta = MagicMock()
    meta.columns = {name: _make_column_meta(cql_type) for name, cql_type in columns_map.items()}
    return meta


class TestWriteRow:
    def test_writes_csv_line_and_resets_buffer(self):
        output, csv_writer = _init_csv_writer()

        result = _write_row(output, csv_writer, ["a", "b", "c"])

        assert result.strip() == "a,b,c"
        assert output.getvalue() == ""


class TestCreateCsvReader:
    def test_decodes_utf8_content(self):
        csv_bytes = b"name,age\nalice,30\n"

        reader = _create_csv_reader(csv_bytes)
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["name"] == "alice"
        assert rows[0]["age"] == "30"


class TestPrepareInsertData:
    def test_skips_empty_column_names(self):
        meta = _make_table_metadata({"name": "text"})
        row = {"name": "alice", "": "junk"}

        columns, values = _prepare_insert_data(row, meta)

        assert columns == ["name"]
        assert values == ["alice"]

    def test_raises_on_unknown_column(self):
        meta = _make_table_metadata({"name": "text"})
        row = {"unknown_col": "value"}

        with pytest.raises(ValueError, match="Unknown column: unknown_col"):
            _prepare_insert_data(row, meta)

    @patch("cassanova.api.dependencies.csv_handler.convert_value_for_cql")
    def test_converts_values_via_converter(self, mock_convert):
        mock_convert.return_value = 42
        meta = _make_table_metadata({"age": "int"})
        row = {"age": "42"}

        columns, values = _prepare_insert_data(row, meta)

        mock_convert.assert_called_once_with("42", "int")
        assert columns == ["age"]
        assert values == [42]


class TestLoadCsvData:
    def _build_csv_bytes(self, header: str, *data_rows: str) -> bytes:
        lines = [header, *list(data_rows)]
        return "\n".join(lines).encode("utf-8")

    def test_successful_batch_import(self):
        csv_bytes = self._build_csv_bytes("name,age", "alice,30", "bob,25")
        meta = _make_table_metadata({"name": "text", "age": "int"})
        session = MagicMock()

        result = load_csv_data(csv_bytes, "ks", "tbl", meta, session)

        assert result["success"] == 2
        assert result["failed"] == 0
        assert result["errors"] == []

    def test_error_collection_capped_at_fifty(self):
        rows = [f"name{i},val{i}" for i in range(60)]
        csv_bytes = self._build_csv_bytes("name,age", *rows)
        meta = _make_table_metadata({"name": "text", "age": "int"})
        session = MagicMock()
        session.execute.side_effect = Exception("batch fail")

        result = load_csv_data(csv_bytes, "ks", "tbl", meta, session)

        assert result["failed"] > 50
        assert len(result["errors"]) <= 10

    def test_partial_success_reported(self):
        csv_bytes = self._build_csv_bytes("name,age", "alice,30", "bob,bad", "carol,25")
        meta = _make_table_metadata({"name": "text", "age": "int"})
        session = MagicMock()

        call_count = 0

        def side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1

        session.execute.side_effect = side_effect

        with patch("cassanova.api.dependencies.csv_handler.convert_value_for_cql") as mock_convert:

            def convert_side_effect(value, cql_type):
                if cql_type == "int" and value == "bad":
                    raise ValueError("Cannot convert 'bad' to int")
                if cql_type == "int":
                    return int(value)
                return value

            mock_convert.side_effect = convert_side_effect
            result = load_csv_data(csv_bytes, "ks", "tbl", meta, session)

        assert result["success"] > 0
        assert result["failed"] > 0

    def test_unknown_column_reported_as_error(self):
        csv_bytes = self._build_csv_bytes("name,bogus", "alice,junk")
        meta = _make_table_metadata({"name": "text"})
        session = MagicMock()

        result = load_csv_data(csv_bytes, "ks", "tbl", meta, session)

        assert result["failed"] > 0
        assert any("Unknown column" in e for e in result["errors"])


class TestGenerateCsvStream:
    def _make_row(self, headers, values):
        row = MagicMock()
        for h, v in zip(headers, values, strict=False):
            setattr(row, h, v)
        return row

    def test_yields_header_row_first(self):
        session = MagicMock()
        result_set = MagicMock()
        result_set.column_names = ["id", "name"]
        result_set.__iter__ = MagicMock(return_value=iter([]))
        session.execute.return_value = result_set

        rows = list(generate_csv_stream(session, "SELECT * FROM t"))

        assert len(rows) == 1
        assert "id" in rows[0]
        assert "name" in rows[0]

    def test_yields_data_rows(self):
        session = MagicMock()
        result_set = MagicMock()
        headers = ["id", "name"]
        result_set.column_names = headers
        data_row = self._make_row(headers, [1, "alice"])
        result_set.__iter__ = MagicMock(return_value=iter([data_row]))
        session.execute.return_value = result_set

        rows = list(generate_csv_stream(session, "SELECT * FROM t"))

        assert len(rows) == 2
        assert "id,name" in rows[0]
        assert "1,alice" in rows[1]

    def test_isoformat_for_datetime_values(self):
        session = MagicMock()
        result_set = MagicMock()
        headers = ["id", "created"]
        result_set.column_names = headers
        dt = datetime(2025, 6, 15, 12, 30, 0)
        data_row = self._make_row(headers, [1, dt])
        result_set.__iter__ = MagicMock(return_value=iter([data_row]))
        session.execute.return_value = result_set

        rows = list(generate_csv_stream(session, "SELECT * FROM t"))

        assert dt.isoformat() in rows[1]
