import json
import logging

import pytest

from cassanova.config._json_log_formatter import JsonFormatter


@pytest.fixture
def formatter():
    return JsonFormatter()


def _make_record(**overrides) -> logging.LogRecord:
    defaults = {
        "name": "cassanova.test",
        "level": logging.INFO,
        "pathname": "test.py",
        "lineno": 1,
        "msg": "hello %s",
        "args": ("world",),
        "exc_info": None,
    }
    defaults.update(overrides)
    return logging.LogRecord(**defaults)


class TestJsonFormatter:
    def test_emits_valid_json(self, formatter):
        record = _make_record()
        result = formatter.format(record)
        payload = json.loads(result)
        assert isinstance(payload, dict)

    def test_includes_core_fields(self, formatter):
        record = _make_record()
        payload = json.loads(formatter.format(record))
        assert payload["level"] == "INFO"
        assert payload["logger"] == "cassanova.test"
        assert payload["message"] == "hello world"
        assert "timestamp" in payload

    def test_timestamp_is_iso8601_utc(self, formatter):
        payload = json.loads(formatter.format(_make_record()))
        assert payload["timestamp"].endswith("+00:00")

    def test_includes_exception_info(self, formatter):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc = sys.exc_info()
        record = _make_record(exc_info=exc)
        payload = json.loads(formatter.format(record))
        assert "exception" in payload
        assert "ValueError: boom" in payload["exception"]

    def test_extra_fields_passed_through(self, formatter):
        record = _make_record()
        record.cluster = "prod-east"
        record.request_id = "abc-123"
        payload = json.loads(formatter.format(record))
        assert payload["cluster"] == "prod-east"
        assert payload["request_id"] == "abc-123"

    def test_reserved_keys_not_duplicated(self, formatter):
        record = _make_record()
        payload = json.loads(formatter.format(record))
        # noise like 'msecs', 'pathname', 'process' should not bleed through
        assert "msecs" not in payload
        assert "pathname" not in payload
        assert "process" not in payload

    def test_non_serializable_extra_falls_back_to_str(self, formatter):
        class Opaque:
            def __repr__(self):
                return "<Opaque>"
        record = _make_record()
        record.thing = Opaque()
        payload = json.loads(formatter.format(record))
        assert payload["thing"] == "<Opaque>"
