from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from cassanova.core.session_manager import SessionManager
from cassanova.config.cluster_config import ClusterConnectionConfig


@pytest.fixture(autouse=True)
def _clean_session_manager():
    """Reset SessionManager state before each test."""
    SessionManager._sessions.clear()
    SessionManager._instances.clear()
    yield
    SessionManager._sessions.clear()
    SessionManager._instances.clear()


def _make_config():
    return ClusterConnectionConfig(contact_points=["127.0.0.1"], port=9042)


class TestSessionManager:
    @patch("cassanova.core.session_manager.generate_cluster_connection")
    def test_creates_new_session(self, mock_gen):
        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_cluster.connect.return_value = mock_session
        mock_gen.return_value = mock_cluster

        session = SessionManager.get_session("test_cluster", _make_config())

        assert session is mock_session
        mock_cluster.connect.assert_called_once()

    @patch("cassanova.core.session_manager.generate_cluster_connection")
    def test_caches_session(self, mock_gen):
        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_cluster.connect.return_value = mock_session
        mock_gen.return_value = mock_cluster

        session1 = SessionManager.get_session("cached", _make_config())
        session2 = SessionManager.get_session("cached", _make_config())

        assert session1 is session2
        mock_cluster.connect.assert_called_once()

    @patch("cassanova.core.session_manager.generate_cluster_connection")
    def test_shutdown_all_clears_state(self, mock_gen):
        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_cluster.connect.return_value = mock_session
        mock_gen.return_value = mock_cluster

        SessionManager.get_session("cluster1", _make_config())
        SessionManager.shutdown_all()

        assert len(SessionManager._sessions) == 0
        assert len(SessionManager._instances) == 0
        mock_session.shutdown.assert_called_once()
        mock_cluster.shutdown.assert_called_once()

    @patch("cassanova.core.session_manager.generate_cluster_connection")
    def test_shutdown_logs_errors_without_raising(self, mock_gen):
        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_session.shutdown.side_effect = Exception("Connection lost")
        mock_cluster.connect.return_value = mock_session
        mock_gen.return_value = mock_cluster

        SessionManager.get_session("failing", _make_config())
        SessionManager.shutdown_all()

        assert len(SessionManager._sessions) == 0

    @patch("cassanova.core.session_manager.generate_cluster_connection")
    def test_thread_safety(self, mock_gen):
        """Multiple threads requesting the same cluster should not create duplicate connections."""
        mock_cluster = MagicMock()
        mock_session = MagicMock()
        mock_cluster.connect.return_value = mock_session
        mock_gen.return_value = mock_cluster

        config = _make_config()
        results = []

        def get_session():
            s = SessionManager.get_session("concurrent", config)
            results.append(s)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_session) for _ in range(20)]
            for f in futures:
                f.result()

        assert all(s is mock_session for s in results)
        mock_cluster.connect.assert_called_once()
