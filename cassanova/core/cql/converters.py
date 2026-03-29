from datetime import date, datetime, time
from ipaddress import ip_address
from json import loads
from typing import Any
from uuid import UUID

_INTEGER_TYPES = frozenset({"int", "bigint", "smallint", "tinyint", "varint", "counter"})
_FLOAT_TYPES = frozenset({"float", "double", "decimal"})
_BOOLEAN_TYPES = frozenset({"boolean", "bool"})
_UUID_TYPES = frozenset({"uuid", "timeuuid"})


def convert_value_for_cql(value: Any, cql_type: str) -> Any:
    cql_type = cql_type.lower()

    if value == "" or value is None:
        return None

    try:
        if _is_collection_type(cql_type):
            return loads(value) if isinstance(value, str) else value

        if cql_type in _INTEGER_TYPES:
            return int(value)

        if cql_type in _FLOAT_TYPES:
            return float(value)

        if cql_type in _BOOLEAN_TYPES:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)

        if cql_type in _UUID_TYPES:
            return UUID(str(value))

        if cql_type == "timestamp":
            return _parse_timestamp(value)

        if cql_type == "date":
            return _parse_date(value)

        if cql_type == "time":
            return _parse_time(value)

        if cql_type == "inet":
            return str(ip_address(value))

        if cql_type == "blob":
            return bytes.fromhex(value.replace("0x", ""))

        return value

    except Exception as e:
        raise ValueError(str(e)) from e


def _is_collection_type(cql_type: str) -> bool:
    return (
        cql_type.startswith("list<")
        or cql_type.startswith("set<")
        or cql_type.startswith("map<")
        or cql_type.startswith("frozen<")
        or cql_type.startswith("tuple<")
    )


def _parse_timestamp(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(float(value))
    except (ValueError, TypeError):
        pass
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        from dateutil import parser

        return parser.parse(value)  # type: ignore[no-any-return]
    except (ImportError, ValueError) as e:
        raise ValueError(f"Cannot parse timestamp: {value}") from e


def _parse_date(value: Any) -> date:
    try:
        return date.fromordinal(int(value) + 719162)
    except (ValueError, TypeError):
        pass
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    try:
        from dateutil import parser

        return parser.parse(value).date()  # type: ignore[no-any-return]
    except (ImportError, ValueError) as e:
        raise ValueError(f"Cannot parse date: {value}") from e


def _parse_time(value: Any) -> time:
    try:
        nanos = int(value)
        return time(
            nanos // (3600 * 10**9),
            (nanos % (3600 * 10**9)) // (60 * 10**9),
            (nanos % (60 * 10**9)) // 10**9,
            (nanos % 10**9) // 1000,
        )
    except (ValueError, TypeError):
        pass
    try:
        return time.fromisoformat(value)
    except ValueError:
        pass
    try:
        from dateutil import parser

        return parser.parse(value).time()  # type: ignore[no-any-return]
    except (ImportError, ValueError) as e:
        raise ValueError(f"Cannot parse time: {value}") from e
