from unittest.mock import MagicMock, patch

import pytest

from cassanova.core.k8s_discovery import (
    KubernetesDiscoveryError,
    _build_service_names,
    _discover_service_contact_points,
    discover_k8s_clusters,
)


def _make_svc(
    svc_type: str = "ClusterIP",
    cluster_ip: str = "10.0.0.5",
    lb_ingress: list[dict] | None = None,
    external_ips: list[str] | None = None,
) -> MagicMock:
    svc = MagicMock()
    svc.spec.type = svc_type
    svc.spec.cluster_ip = cluster_ip
    svc.spec.external_i_ps = external_ips or []

    if lb_ingress:
        ingress_objs = []
        for entry in lb_ingress:
            ing = MagicMock()
            ing.ip = entry.get("ip")
            ing.hostname = entry.get("hostname")
            ingress_objs.append(ing)
        svc.status.load_balancer.ingress = ingress_objs
    else:
        svc.status.load_balancer.ingress = []

    return svc


class TestDiscoverServiceContactPoints:
    def _make_core_api(self, svc: MagicMock) -> MagicMock:
        core_api = MagicMock()
        core_api.read_namespaced_service.return_value = svc
        return core_api

    def test_external_only_skips_cluster_ip_and_dns(self) -> None:
        svc = _make_svc(svc_type="ClusterIP", cluster_ip="10.0.0.5")
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result is None

    def test_external_only_skips_dns_fallback(self) -> None:
        svc = _make_svc(svc_type="ClusterIP", cluster_ip="None")
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result is None

    def test_external_only_keeps_lb_ingress_ip(self) -> None:
        svc = _make_svc(svc_type="LoadBalancer", lb_ingress=[{"ip": "192.168.1.10"}])
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result == ["192.168.1.10"]

    def test_external_only_keeps_lb_ingress_hostname(self) -> None:
        svc = _make_svc(svc_type="LoadBalancer", lb_ingress=[{"hostname": "cass.example.com"}])
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result == ["cass.example.com"]

    def test_external_only_keeps_external_ips(self) -> None:
        svc = _make_svc(svc_type="ClusterIP", external_ips=["172.16.0.1", "172.16.0.2"])
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result == ["172.16.0.1", "172.16.0.2"]

    def test_external_only_concatenates_lb_and_external_ips(self) -> None:
        svc = _make_svc(
            svc_type="LoadBalancer",
            lb_ingress=[{"ip": "192.168.1.10"}],
            external_ips=["172.16.0.1"],
        )
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=True)

        assert result == ["192.168.1.10", "172.16.0.1"]

    def test_default_mode_falls_back_to_cluster_ip(self) -> None:
        svc = _make_svc(svc_type="ClusterIP", cluster_ip="10.0.0.5")
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "svc", "ns", external_only=False)

        assert result == ["10.0.0.5"]

    def test_default_mode_falls_back_to_dns_when_no_cluster_ip(self) -> None:
        svc = _make_svc(svc_type="ClusterIP", cluster_ip="None")
        core_api = self._make_core_api(svc)

        result = _discover_service_contact_points(core_api, "mysvc", "mynamespace", external_only=False)

        assert result == ["mysvc.mynamespace.svc.cluster.local"]

    def test_returns_none_on_api_exception(self) -> None:
        from kubernetes.client import ApiException

        core_api = MagicMock()
        core_api.read_namespaced_service.side_effect = ApiException(status=404)

        result = _discover_service_contact_points(core_api, "svc", "ns")

        assert result is None


class TestBuildServiceNames:
    def test_suffix_generates_primary_and_fallback_name(self) -> None:
        names = _build_service_names("mycluster", "dc1", "-svc")
        assert names == ["mycluster-dc1-svc", "mycluster-dc1-service"]

    def test_empty_suffix_skips_primary(self) -> None:
        names = _build_service_names("mycluster", "dc1", "")
        assert names == ["mycluster-dc1-service"]


class TestDiscoverK8sClusters:
    @patch("cassanova.core.k8s_discovery.K8S_AVAILABLE", False)
    def test_returns_empty_when_k8s_not_installed(self) -> None:
        result = discover_k8s_clusters()
        assert result == {}

    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    @patch("cassanova.core.k8s_discovery._discover_for_context")
    def test_raises_when_all_contexts_fail(
        self, mock_discover: MagicMock, mock_resolve: MagicMock
    ) -> None:
        mock_resolve.return_value = ["ctx-a", "ctx-b"]
        mock_discover.side_effect = KubernetesDiscoveryError("unreachable")

        with pytest.raises(KubernetesDiscoveryError, match="No kubeconfig contexts could be reached"):
            discover_k8s_clusters(kubeconfig_path="/fake/kubeconfig")

    @patch("cassanova.core.k8s_discovery._resolve_contexts")
    @patch("cassanova.core.k8s_discovery._discover_for_context")
    def test_partial_context_failure_returns_successful_results(
        self, mock_discover: MagicMock, mock_resolve: MagicMock
    ) -> None:
        from cassanova.config.cluster_config import ClusterConnectionConfig
        from cassanova.core.k8s_discovery import DiscoveredCluster

        mock_resolve.return_value = ["ctx-a", "ctx-b"]
        good_cluster = DiscoveredCluster(
            config=ClusterConnectionConfig(contact_points=["1.2.3.4"], port=9042),
            context="ctx-a",
        )
        mock_discover.side_effect = [
            {"good-cluster": good_cluster},
            KubernetesDiscoveryError("unreachable"),
        ]

        result = discover_k8s_clusters(kubeconfig_path="/fake/kubeconfig")

        assert "good-cluster" in result
        assert result["good-cluster"] == good_cluster
