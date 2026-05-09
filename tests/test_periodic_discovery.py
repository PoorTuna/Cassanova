from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from cassanova.api.bootstrap import _run_discovery_pass
from cassanova.config.cluster_config import ClusterConnectionConfig
from cassanova.config.cluster_metadata import ClusterMetadata
from cassanova.core.k8s_discovery import DiscoveredCluster


def _make_cluster_config(contact_point: str = "1.2.3.4") -> ClusterConnectionConfig:
    return ClusterConnectionConfig(contact_points=[contact_point], port=9042)


def _make_discovered(name: str, ctx: str = "ctx", contact_point: str = "1.2.3.4") -> dict:
    return {
        name: DiscoveredCluster(
            config=_make_cluster_config(contact_point),
            context=ctx,
        )
    }


def _make_config(
    clusters: dict | None = None,
    cluster_metadata: dict | None = None,
    stale_threshold: int = 3,
    external_only: bool = False,
) -> MagicMock:
    config = MagicMock()
    config.clusters = clusters or {}
    config.cluster_metadata = cluster_metadata or {}
    config.k8s.kubeconfig = None
    config.k8s.namespace = None
    config.k8s.suffix = "-service"
    config.k8s.contexts = None
    config.k8s.external_only = external_only
    config.k8s.stale_threshold = stale_threshold
    return config


class TestRunDiscoveryPass:
    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_adds_new_clusters_to_config(self, mock_discover: MagicMock) -> None:
        mock_discover.return_value = _make_discovered("new-cluster")
        config = _make_config()

        _run_discovery_pass(config)

        assert "new-cluster" in config.clusters
        assert config.cluster_metadata["new-cluster"].source == "k8s"
        assert config.cluster_metadata["new-cluster"].miss_count == 0

    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_resets_miss_count_on_rediscovery(self, mock_discover: MagicMock) -> None:
        mock_discover.return_value = _make_discovered("cluster-a")
        existing_meta = ClusterMetadata(source="k8s", context="ctx", miss_count=2)
        config = _make_config(
            clusters={"cluster-a": _make_cluster_config()},
            cluster_metadata={"cluster-a": existing_meta},
        )

        _run_discovery_pass(config)

        assert config.cluster_metadata["cluster-a"].miss_count == 0

    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_increments_miss_count_for_absent_cluster(self, mock_discover: MagicMock) -> None:
        mock_discover.return_value = {}
        existing_meta = ClusterMetadata(source="k8s", context="ctx", miss_count=0)
        config = _make_config(
            clusters={"cluster-a": _make_cluster_config()},
            cluster_metadata={"cluster-a": existing_meta},
            stale_threshold=3,
        )

        _run_discovery_pass(config)

        assert config.cluster_metadata["cluster-a"].miss_count == 1

    @patch("cassanova.api.bootstrap.session_manager")
    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_evicts_cluster_after_stale_threshold(
        self, mock_discover: MagicMock, mock_session_manager: MagicMock
    ) -> None:
        mock_discover.return_value = {}
        existing_meta = ClusterMetadata(source="k8s", context="ctx", miss_count=2)
        config = _make_config(
            clusters={"cluster-a": _make_cluster_config()},
            cluster_metadata={"cluster-a": existing_meta},
            stale_threshold=3,
        )

        _run_discovery_pass(config)

        assert "cluster-a" not in config.clusters
        assert "cluster-a" not in config.cluster_metadata
        mock_session_manager.shutdown.assert_called_once_with("cluster-a")

    @patch("cassanova.api.bootstrap.session_manager")
    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_scan_failure_does_not_increment_miss_count(
        self, mock_discover: MagicMock, mock_session_manager: MagicMock
    ) -> None:
        from cassanova.core.k8s_discovery import KubernetesDiscoveryError

        mock_discover.side_effect = KubernetesDiscoveryError("API unreachable")
        existing_meta = ClusterMetadata(source="k8s", context="ctx", miss_count=1)
        config = _make_config(
            clusters={"cluster-a": _make_cluster_config()},
            cluster_metadata={"cluster-a": existing_meta},
        )

        _run_discovery_pass(config)

        assert config.cluster_metadata["cluster-a"].miss_count == 1
        mock_session_manager.shutdown.assert_not_called()

    @patch("cassanova.api.bootstrap.session_manager")
    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_static_clusters_never_evicted(
        self, mock_discover: MagicMock, mock_session_manager: MagicMock
    ) -> None:
        mock_discover.return_value = {}
        static_meta = ClusterMetadata(source="static")
        config = _make_config(
            clusters={"static-cluster": _make_cluster_config()},
            cluster_metadata={"static-cluster": static_meta},
            stale_threshold=1,
        )

        _run_discovery_pass(config)

        assert "static-cluster" in config.clusters
        mock_session_manager.shutdown.assert_not_called()

    @patch("cassanova.api.bootstrap.session_manager")
    @patch("cassanova.api.bootstrap.discover_k8s_clusters")
    def test_vanish_then_return_resets_to_zero(
        self, mock_discover: MagicMock, mock_session_manager: MagicMock
    ) -> None:
        existing_meta = ClusterMetadata(source="k8s", context="ctx", miss_count=1)
        config = _make_config(
            clusters={"cluster-a": _make_cluster_config()},
            cluster_metadata={"cluster-a": existing_meta},
            stale_threshold=3,
        )

        mock_discover.return_value = _make_discovered("cluster-a")
        _run_discovery_pass(config)

        assert config.cluster_metadata["cluster-a"].miss_count == 0
        mock_session_manager.shutdown.assert_not_called()
