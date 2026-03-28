from collections import namedtuple
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from cassandra import InvalidRequest, ConsistencyLevel
from cassandra.protocol import SyntaxException
from cassandra.cluster import NoHostAvailable

from cassanova.core.cql.execute_query import execute_query_cql, get_trace_info
from cassanova.models.cql_query import CQLQuery


Row = namedtuple("Row", ["id", "name"])


def _make_query(cql="SELECT * FROM ks.tbl", cl=ConsistencyLevel.QUORUM, tracing=False):
    return CQLQuery(cql=cql, cl=cl, enable_tracing=tracing)


class TestExecuteQueryCql:
    def test_successful_query(self, mock_session):
        mock_session.execute.return_value = [Row(id=1, name="alice")]
        result = execute_query_cql(mock_session, _make_query())
        assert "result" in result
        assert result["result"][0]["id"] == 1

    def test_syntax_error_returns_string(self, mock_session):
        mock_session.execute.side_effect = SyntaxException(
            code=0x2000, message="bad syntax", info=None
        )
        result = execute_query_cql(mock_session, _make_query("SELCT *"))
        assert isinstance(result, str)

    def test_no_host_available_returns_string(self, mock_session):
        mock_session.execute.side_effect = NoHostAvailable("no hosts", {})
        result = execute_query_cql(mock_session, _make_query())
        assert isinstance(result, str)

    def test_invalid_request_returns_string(self, mock_session):
        mock_session.execute.side_effect = InvalidRequest("table xyz does not exist")
        mock_session.cluster.metadata.keyspaces = {}
        result = execute_query_cql(mock_session, _make_query())
        assert isinstance(result, str)

    def test_case_insensitive_retry(self, mock_session):
        """When a table name has wrong case, it should retry with the correct case."""
        mock_session.execute.side_effect = [
            InvalidRequest("unconfigured table mytable"),
            [Row(id=1, name="test")],
        ]

        ks_meta = MagicMock()
        ks_meta.tables = {"MyTable": MagicMock()}
        mock_session.cluster.metadata.keyspaces = {"ks": ks_meta}

        result = execute_query_cql(
            mock_session, _make_query("SELECT * FROM ks.mytable")
        )
        assert "result" in result
        assert mock_session.execute.call_count == 2

    def test_retry_limited_to_one_attempt(self, mock_session):
        """Retry should not recurse beyond attempt 2."""
        mock_session.execute.side_effect = InvalidRequest("table xyz does not exist")
        mock_session.cluster.metadata.keyspaces = {}

        result = execute_query_cql(mock_session, _make_query())
        assert isinstance(result, str)
        assert mock_session.execute.call_count == 1

    def test_unexpected_exception_propagates(self, mock_session):
        mock_session.execute.side_effect = RuntimeError("unexpected")
        with pytest.raises(RuntimeError, match="unexpected"):
            execute_query_cql(mock_session, _make_query())


class TestGetTraceInfo:
    def test_extracts_trace_info(self):
        mock_event = MagicMock()
        mock_event.description = "Reading data"
        mock_event.source = "10.0.0.1"
        mock_event.source_elapsed.total_seconds.return_value = 0.005

        mock_trace = MagicMock()
        mock_trace.request_type = "Execute CQL3 query"
        mock_trace.duration = 5000
        mock_trace.coordinator = "10.0.0.1"
        mock_trace.parameters = {"query": "SELECT *"}
        mock_trace.events = [mock_event]

        mock_result_set = MagicMock()
        mock_result_set.get_query_trace.return_value = mock_trace

        info = get_trace_info(mock_result_set)

        assert info["request_type"] == "Execute CQL3 query"
        assert info["duration_ms"] == 5.0
        assert len(info["events"]) == 1
        assert info["events"][0]["description"] == "Reading data"

    def test_zero_duration_uses_max_event(self):
        mock_event = MagicMock()
        mock_event.description = "test"
        mock_event.source = "10.0.0.1"
        mock_event.source_elapsed.total_seconds.return_value = 0.010

        mock_trace = MagicMock()
        mock_trace.request_type = "Query"
        mock_trace.duration = 0
        mock_trace.coordinator = "10.0.0.1"
        mock_trace.parameters = {}
        mock_trace.events = [mock_event]

        mock_result_set = MagicMock()
        mock_result_set.get_query_trace.return_value = mock_trace

        info = get_trace_info(mock_result_set)
        assert info["duration_ms"] == 10.0
