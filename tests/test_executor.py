"""Tests for the central CQL executor."""

import json
from unittest.mock import MagicMock, patch

import pytest
from cassandra.query import BatchStatement, SimpleStatement

from cassanova.core.cql._executor import _detect_action, _is_mutation, execute_cql
from cassanova.exceptions.cql_exceptions import CQLPermissionDenied, ReadOnlyClusterError
from cassanova.models.auth_models import WebUser


def _make_user(roles: list[str]) -> WebUser:
    return WebUser(username="testuser", password="hashed", roles=roles)


class TestMutationDetection:
    @pytest.mark.parametrize(
        "cql,expected",
        [
            ("INSERT INTO t (id) VALUES (1)", True),
            ("UPDATE t SET x=1 WHERE id=1", True),
            ("DELETE FROM t WHERE id=1", True),
            ("DROP TABLE t", True),
            ("TRUNCATE t", True),
            ("ALTER TABLE t ADD col text", True),
            ("CREATE TABLE t (id int PRIMARY KEY)", True),
            ("GRANT SELECT ON t TO role", True),
            ("REVOKE SELECT ON t FROM role", True),
            ("SELECT * FROM t", False),
            ("DESCRIBE TABLE t", False),
            ("LIST ALL PERMISSIONS OF role", False),
            ("  drop TABLE t  ", True),
            ("  select * from t", False),
            ("", False),
        ],
    )
    def test_is_mutation(self, cql: str, expected: bool) -> None:
        assert _is_mutation(cql) == expected

    def test_batch_statement_is_mutation(self) -> None:
        batch = BatchStatement()
        assert _is_mutation(batch) is True

    def test_simple_statement(self) -> None:
        stmt = SimpleStatement("INSERT INTO t (id) VALUES (1)")
        assert _is_mutation(stmt) is True

    def test_simple_statement_select(self) -> None:
        stmt = SimpleStatement("SELECT * FROM t")
        assert _is_mutation(stmt) is False

    def test_detect_action(self) -> None:
        assert _detect_action("DROP TABLE t") == "DROP"
        assert _detect_action("select * from t") == "SELECT"
        assert _detect_action(BatchStatement()) == "BATCH"
        assert _detect_action(SimpleStatement("INSERT INTO t (id) VALUES (1)")) == "INSERT"


class TestReadOnlyMode:
    @patch("cassanova.core.cql._executor.get_clusters_config")
    def test_mutation_blocked_on_read_only(self, mock_config: MagicMock) -> None:
        cluster_config = MagicMock()
        cluster_config.read_only = True
        mock_config.return_value.clusters = {"prod": cluster_config}

        session = MagicMock()
        admin = _make_user(["admin"])

        with pytest.raises(ReadOnlyClusterError):
            execute_cql(session, "DROP TABLE t", "prod", admin)

    @patch("cassanova.core.cql._executor.get_clusters_config")
    def test_select_allowed_on_read_only(self, mock_config: MagicMock) -> None:
        session = MagicMock()
        execute_cql(session, "SELECT * FROM t", "prod", None)
        session.execute.assert_called_once()


class TestRBACEnforcement:
    @patch("cassanova.core.cql._executor.get_clusters_config")
    @patch("cassanova.core.cql._executor.check_permission", return_value=False)
    def test_viewer_cannot_drop(self, mock_perm: MagicMock, mock_config: MagicMock) -> None:
        cluster_config = MagicMock()
        cluster_config.read_only = False
        mock_config.return_value.clusters = {"dev": cluster_config}

        session = MagicMock()
        viewer = _make_user(["viewer"])

        with pytest.raises(CQLPermissionDenied):
            execute_cql(session, "DROP TABLE t", "dev", viewer)

    @patch("cassanova.core.cql._executor.get_clusters_config")
    @patch("cassanova.core.cql._executor.check_permission", return_value=True)
    def test_admin_can_drop(self, mock_perm: MagicMock, mock_config: MagicMock) -> None:
        cluster_config = MagicMock()
        cluster_config.read_only = False
        mock_config.return_value.clusters = {"dev": cluster_config}

        session = MagicMock()
        admin = _make_user(["admin"])

        execute_cql(session, "DROP TABLE t", "dev", admin)
        session.execute.assert_called_once()


class TestAuditLogging:
    @patch("cassanova.core.cql._executor.get_clusters_config")
    @patch("cassanova.core.cql._executor.check_permission", return_value=True)
    @patch("cassanova.core.cql._executor._audit_logger")
    def test_mutation_is_logged(
        self, mock_logger: MagicMock, mock_perm: MagicMock, mock_config: MagicMock
    ) -> None:
        cluster_config = MagicMock()
        cluster_config.read_only = False
        mock_config.return_value.clusters = {"dev": cluster_config}

        session = MagicMock()
        admin = _make_user(["admin"])

        execute_cql(session, "DROP TABLE users", "dev", admin)

        mock_logger.info.assert_called_once()
        log_line = json.loads(mock_logger.info.call_args[0][0])
        assert log_line["user"] == "testuser"
        assert log_line["cluster"] == "dev"
        assert log_line["action"] == "DROP"
        assert "DROP TABLE users" in log_line["query"]

    @patch("cassanova.core.cql._executor.get_clusters_config")
    @patch("cassanova.core.cql._executor.check_permission", return_value=True)
    @patch("cassanova.core.cql._executor._audit_logger")
    def test_select_not_logged(
        self, mock_logger: MagicMock, mock_perm: MagicMock, mock_config: MagicMock
    ) -> None:
        session = MagicMock()
        execute_cql(session, "SELECT * FROM t", "dev", None)
        mock_logger.info.assert_not_called()
