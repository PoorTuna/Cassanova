from unittest.mock import MagicMock, call, patch

import pytest

from cassanova.core.k8s_discovery import _cluster_name_allowed, discover_k8s_clusters


class TestClusterNameAllowed:
    def test_empty_include_and_exclude_allows_all(self) -> None:
        assert _cluster_name_allowed("prod-eu", [], []) is True

    def test_include_pattern_matches(self) -> None:
        assert _cluster_name_allowed("prod-eu", ["prod-*"], []) is True

    def test_include_pattern_rejects_non_match(self) -> None:
        assert _cluster_name_allowed("dev-eu", ["prod-*"], []) is False

    def test_exclude_pattern_rejects_match(self) -> None:
        assert _cluster_name_allowed("a-test", [], ["*-test"]) is False

    def test_exclude_non_match_allows(self) -> None:
        assert _cluster_name_allowed("anything", [], ["*-test"]) is True

    def test_exclude_wins_over_include(self) -> None:
        assert _cluster_name_allowed("prod-dev", ["prod-*"], ["*-dev"]) is False

    def test_multiple_include_patterns_any_match(self) -> None:
        assert _cluster_name_allowed("staging-eu", ["prod-*", "staging-*"], []) is True

    def test_multiple_exclude_patterns(self) -> None:
        assert _cluster_name_allowed("dev-eu", [], ["*-dev", "*-test"]) is True
        assert _cluster_name_allowed("ci-test", [], ["*-dev", "*-test"]) is False

    def test_case_sensitive(self) -> None:
        assert _cluster_name_allowed("PROD-EU", ["prod-*"], []) is False
        assert _cluster_name_allowed("prod-eu", ["PROD-*"], []) is False

    def test_question_mark_wildcard(self) -> None:
        assert _cluster_name_allowed("prod-a", ["prod-?"], []) is True
        assert _cluster_name_allowed("prod-ab", ["prod-?"], []) is False

    def test_character_class_wildcard(self) -> None:
        assert _cluster_name_allowed("prod-1", ["prod-[0-9]"], []) is True
        assert _cluster_name_allowed("prod-x", ["prod-[0-9]"], []) is False


class TestDiscoverK8sClustersFiltering:
    def _make_cr(self, name: str, namespace: str = "default") -> dict:
        return {
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"cassandra": {"datacenters": [{"metadata": {"name": "dc1"}}]}},
        }

    def _make_custom_api(self, cluster_names: list[str]) -> MagicMock:
        custom_api = MagicMock()
        custom_api.list_cluster_custom_object.return_value = {
            "items": [self._make_cr(n) for n in cluster_names]
        }
        return custom_api

    def _make_core_api_with_lb(self, ip: str = "10.0.0.1") -> MagicMock:
        svc = MagicMock()
        svc.spec.type = "LoadBalancer"
        svc.spec.cluster_ip = ip
        svc.spec.external_ips = []
        ing = MagicMock()
        ing.ip = ip
        ing.hostname = None
        svc.status.load_balancer.ingress = [ing]

        secret = MagicMock()
        secret.data = {
            "username": __import__("base64").b64encode(b"admin").decode(),
            "password": __import__("base64").b64encode(b"secret").decode(),
        }

        core_api = MagicMock()
        core_api.read_namespaced_service.return_value = svc
        core_api.read_namespaced_secret.return_value = secret
        return core_api

    @patch("cassanova.core.k8s_discovery.client")
    @patch("cassanova.core.k8s_discovery._load_k8s_config")
    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    def test_include_filter_skips_non_matching_clusters(
        self, mock_resolve: MagicMock, mock_load: MagicMock, mock_client: MagicMock
    ) -> None:
        mock_resolve.return_value = None
        core_api = self._make_core_api_with_lb()
        mock_client.CoreV1Api.return_value = core_api
        mock_client.CustomObjectsApi.return_value = self._make_custom_api(
            ["prod-eu", "dev-eu", "prod-us"]
        )

        result = discover_k8s_clusters(cluster_include=["prod-*"])

        assert set(result.keys()) == {"prod-eu", "prod-us"}
        assert "dev-eu" not in result

    @patch("cassanova.core.k8s_discovery.client")
    @patch("cassanova.core.k8s_discovery._load_k8s_config")
    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    def test_exclude_filter_drops_matching_clusters(
        self, mock_resolve: MagicMock, mock_load: MagicMock, mock_client: MagicMock
    ) -> None:
        mock_resolve.return_value = None
        core_api = self._make_core_api_with_lb()
        mock_client.CoreV1Api.return_value = core_api
        mock_client.CustomObjectsApi.return_value = self._make_custom_api(
            ["prod-eu", "dev-eu", "ci-test"]
        )

        result = discover_k8s_clusters(cluster_exclude=["dev-*", "*-test"])

        assert set(result.keys()) == {"prod-eu"}

    @patch("cassanova.core.k8s_discovery.client")
    @patch("cassanova.core.k8s_discovery._load_k8s_config")
    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    def test_filtered_cluster_does_not_read_secret(
        self, mock_resolve: MagicMock, mock_load: MagicMock, mock_client: MagicMock
    ) -> None:
        mock_resolve.return_value = None
        core_api = self._make_core_api_with_lb()
        mock_client.CoreV1Api.return_value = core_api
        mock_client.CustomObjectsApi.return_value = self._make_custom_api(["dev-eu"])

        discover_k8s_clusters(cluster_include=["prod-*"])

        core_api.read_namespaced_secret.assert_not_called()
        core_api.read_namespaced_service.assert_not_called()

    @patch("cassanova.core.k8s_discovery.client")
    @patch("cassanova.core.k8s_discovery._load_k8s_config")
    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    def test_no_filters_discovers_all(
        self, mock_resolve: MagicMock, mock_load: MagicMock, mock_client: MagicMock
    ) -> None:
        mock_resolve.return_value = None
        core_api = self._make_core_api_with_lb()
        mock_client.CoreV1Api.return_value = core_api
        mock_client.CustomObjectsApi.return_value = self._make_custom_api(
            ["prod-eu", "dev-eu", "staging"]
        )

        result = discover_k8s_clusters()

        assert set(result.keys()) == {"prod-eu", "dev-eu", "staging"}
