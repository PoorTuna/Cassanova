import pytest

from cassanova.core.cql.sanitize_input import sanitize_identifier


class TestSanitizeIdentifier:
    def test_valid_simple_name(self):
        assert sanitize_identifier("users") == "users"

    def test_valid_with_underscore(self):
        assert sanitize_identifier("my_table") == "my_table"

    def test_valid_with_numbers(self):
        assert sanitize_identifier("table123") == "table123"

    def test_valid_underscore_prefix(self):
        assert sanitize_identifier("_internal") == "_internal"

    def test_valid_mixed_case(self):
        assert sanitize_identifier("MyKeyspace") == "MyKeyspace"

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("")

    def test_rejects_starts_with_number(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("123abc")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("my table")

    def test_rejects_semicolon(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("users; DROP TABLE")

    def test_rejects_single_quotes(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("users'--")

    def test_rejects_double_quotes(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier('users"')

    def test_rejects_parentheses(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("users()")

    def test_rejects_dot(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("keyspace.table")

    def test_rejects_hyphen(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("my-table")

    def test_rejects_newline(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            sanitize_identifier("users\n; DROP TABLE foo")
