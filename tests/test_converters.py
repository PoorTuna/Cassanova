from datetime import date, datetime, time
from uuid import UUID

import pytest

from cassanova.core.cql.converters import convert_value_for_cql


class TestNullAndEmpty:
    def test_none_returns_none(self):
        assert convert_value_for_cql(None, "text") is None

    def test_empty_string_returns_none(self):
        assert convert_value_for_cql("", "text") is None

    def test_none_with_int_type_returns_none(self):
        assert convert_value_for_cql(None, "int") is None

    def test_empty_string_with_int_type_returns_none(self):
        assert convert_value_for_cql("", "int") is None


class TestCollectionTypes:
    def test_list_from_json_string(self):
        assert convert_value_for_cql("[1, 2, 3]", "list<int>") == [1, 2, 3]

    def test_set_from_json_string(self):
        assert convert_value_for_cql("[1, 2, 3]", "set<int>") == [1, 2, 3]

    def test_map_from_json_string(self):
        result = convert_value_for_cql('{"a": 1}', "map<text, int>")
        assert result == {"a": 1}

    def test_frozen_from_json_string(self):
        assert convert_value_for_cql("[1, 2]", "frozen<list<int>>") == [1, 2]

    def test_tuple_from_json_string(self):
        assert convert_value_for_cql('[1, "a"]', "tuple<int, text>") == [1, "a"]

    def test_list_already_parsed(self):
        assert convert_value_for_cql([1, 2, 3], "list<int>") == [1, 2, 3]

    def test_set_already_parsed(self):
        assert convert_value_for_cql({1, 2}, "set<int>") == {1, 2}

    def test_map_already_parsed(self):
        assert convert_value_for_cql({"a": 1}, "map<text, int>") == {"a": 1}

    def test_frozen_already_parsed(self):
        assert convert_value_for_cql([1], "frozen<list<int>>") == [1]

    def test_tuple_already_parsed(self):
        assert convert_value_for_cql([1, "a"], "tuple<int, text>") == [1, "a"]


class TestCollectionTypePrecedence:
    def test_map_text_int_parses_as_collection_not_integer(self):
        result = convert_value_for_cql('{"k": 1}', "map<text, int>")
        assert isinstance(result, dict)

    def test_frozen_list_int_parses_as_collection_not_integer(self):
        result = convert_value_for_cql("[1, 2]", "frozen<list<int>>")
        assert isinstance(result, list)

    def test_set_bigint_parses_as_collection_not_integer(self):
        result = convert_value_for_cql("[100]", "set<bigint>")
        assert isinstance(result, list)

    def test_list_double_parses_as_collection_not_float(self):
        result = convert_value_for_cql("[1.5]", "list<double>")
        assert isinstance(result, list)


class TestIntegerTypes:
    @pytest.mark.parametrize(
        "cql_type",
        [
            "int",
            "bigint",
            "smallint",
            "tinyint",
            "varint",
            "counter",
        ],
    )
    def test_string_to_int(self, cql_type):
        assert convert_value_for_cql("42", cql_type) == 42

    @pytest.mark.parametrize(
        "cql_type",
        [
            "int",
            "bigint",
            "smallint",
            "tinyint",
            "varint",
            "counter",
        ],
    )
    def test_negative_string_to_int(self, cql_type):
        assert convert_value_for_cql("-7", cql_type) == -7

    def test_case_insensitive_type(self):
        assert convert_value_for_cql("10", "INT") == 10
        assert convert_value_for_cql("10", "BigInt") == 10


class TestFloatTypes:
    @pytest.mark.parametrize("cql_type", ["float", "double", "decimal"])
    def test_string_to_float(self, cql_type):
        assert convert_value_for_cql("3.14", cql_type) == pytest.approx(3.14)

    @pytest.mark.parametrize("cql_type", ["float", "double", "decimal"])
    def test_negative_string_to_float(self, cql_type):
        assert convert_value_for_cql("-2.5", cql_type) == pytest.approx(-2.5)

    def test_integer_string_to_float(self):
        assert convert_value_for_cql("5", "float") == 5.0


class TestBooleanTypes:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_string_values(self, value, expected):
        assert convert_value_for_cql(value, "boolean") is expected

    def test_bool_type_alias(self):
        assert convert_value_for_cql("true", "bool") is True
        assert convert_value_for_cql("false", "bool") is False

    def test_actual_bool_true(self):
        assert convert_value_for_cql(True, "boolean") is True

    def test_actual_bool_false(self):
        assert convert_value_for_cql(False, "boolean") is False

    def test_nonzero_int_is_true(self):
        assert convert_value_for_cql(1, "boolean") is True

    def test_zero_int_is_false(self):
        assert convert_value_for_cql(0, "boolean") is False


class TestUuidTypes:
    def test_valid_uuid(self):
        raw = "550e8400-e29b-41d4-a716-446655440000"
        result = convert_value_for_cql(raw, "uuid")
        assert result == UUID(raw)

    def test_valid_timeuuid(self):
        raw = "550e8400-e29b-11d4-a716-446655440000"
        result = convert_value_for_cql(raw, "timeuuid")
        assert result == UUID(raw)

    def test_invalid_uuid_raises(self):
        with pytest.raises(ValueError):
            convert_value_for_cql("not-a-uuid", "uuid")


class TestTimestampType:
    def test_epoch_float(self):
        result = convert_value_for_cql("0", "timestamp")
        assert isinstance(result, datetime)

    def test_iso_format(self):
        result = convert_value_for_cql("2024-01-15T10:30:00", "timestamp")
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            convert_value_for_cql("not-a-timestamp", "timestamp")


class TestDateType:
    def test_ordinal_int(self):
        result = convert_value_for_cql(0, "date")
        assert isinstance(result, date)

    def test_iso_format(self):
        result = convert_value_for_cql("2024-06-15", "date")
        assert result == date(2024, 6, 15)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            convert_value_for_cql("not-a-date", "date")


class TestTimeType:
    def test_nanoseconds(self):
        nanos = 3_600_000_000_000
        result = convert_value_for_cql(nanos, "time")
        assert isinstance(result, time)
        assert result.hour == 1
        assert result.minute == 0

    def test_iso_format(self):
        result = convert_value_for_cql("13:45:30", "time")
        assert isinstance(result, time)
        assert result.hour == 13
        assert result.minute == 45
        assert result.second == 30

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            convert_value_for_cql("not-a-time", "time")


class TestInetType:
    def test_valid_ipv4(self):
        assert convert_value_for_cql("192.168.1.1", "inet") == "192.168.1.1"

    def test_valid_ipv6(self):
        result = convert_value_for_cql("::1", "inet")
        assert result == "::1"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            convert_value_for_cql("999.999.999.999", "inet")


class TestBlobType:
    def test_hex_string(self):
        result = convert_value_for_cql("deadbeef", "blob")
        assert result == bytes.fromhex("deadbeef")

    def test_0x_prefixed_hex_string(self):
        result = convert_value_for_cql("0xdeadbeef", "blob")
        assert result == bytes.fromhex("deadbeef")


class TestDefaultFallthrough:
    def test_text_returns_unchanged(self):
        assert convert_value_for_cql("hello", "text") == "hello"

    def test_ascii_returns_unchanged(self):
        assert convert_value_for_cql("world", "ascii") == "world"

    def test_varchar_returns_unchanged(self):
        assert convert_value_for_cql("test", "varchar") == "test"
