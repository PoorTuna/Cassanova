from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from cassanova.api.routes.api.admin_routes import list_all_clusters
from cassanova.config.cluster_config import ClusterConnectionConfig, ClusterCredentials
from cassanova.config.cluster_metadata import ClusterMetadata


def _make_cluster_config(
    contact_points: list[str] | None = None,
    port: int = 9042,
    credentials: ClusterCredentials | None = None,
    jmx_credentials: ClusterCredentials | None = None,
    additional_kwargs: dict | None = None,
) -> ClusterConnectionConfig:
    return ClusterConnectionConfig(
        contact_points=contact_points or ["10.0.0.1"],
        port=port,
        credentials=credentials,
        jmx_credentials=jmx_credentials,
        additional_kwargs=additional_kwargs,
    )


def _make_cassanova_config(
    clusters: dict | None = None,
    metadata: dict | None = None,
) -> MagicMock:
    config = MagicMock()
    config.clusters = clusters or {}
    config.cluster_metadata = metadata or {}
    return config


class TestListAllClusters:
    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_returns_static_cluster_with_correct_source(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"prod": _make_cluster_config()},
            metadata={"prod": ClusterMetadata(source="static")},
        )

        result = list_all_clusters()

        assert len(result) == 1
        assert result[0].name == "prod"
        assert result[0].source == "static"
        assert result[0].context is None

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_returns_k8s_cluster_with_provenance(self, mock_get_config: MagicMock) -> None:
        now = datetime.now(UTC)
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"k8s-cluster": _make_cluster_config(contact_points=["192.168.1.5"])},
            metadata={
                "k8s-cluster": ClusterMetadata(
                    source="k8s",
                    context="prod-ctx",
                    discovered_at=now,
                    last_seen=now,
                    miss_count=0,
                )
            },
        )

        result = list_all_clusters()

        assert len(result) == 1
        assert result[0].source == "k8s"
        assert result[0].context == "prod-ctx"
        assert result[0].last_seen == now
        assert result[0].miss_count == 0

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_exposes_credentials_by_default(self, mock_get_config: MagicMock) -> None:
        creds = ClusterCredentials(username="cassandra", password="super_secret")
        jmx_creds = ClusterCredentials(username="jmx_user", password="jmx_secret")
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"prod": _make_cluster_config(credentials=creds, jmx_credentials=jmx_creds)},
            metadata={"prod": ClusterMetadata(source="static")},
        )

        result = list_all_clusters()

        view = result[0]
        assert view.has_credentials is True
        assert view.has_jmx_credentials is True
        assert view.credentials is not None
        assert view.credentials.username == "cassandra"
        assert view.credentials.password == "super_secret"
        assert view.jmx_credentials is not None
        assert view.jmx_credentials.username == "jmx_user"
        assert view.jmx_credentials.password == "jmx_secret"

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_masks_credentials_when_disabled(self, mock_get_config: MagicMock) -> None:
        creds = ClusterCredentials(username="cassandra", password="super_secret")
        jmx_creds = ClusterCredentials(username="jmx_user", password="jmx_secret")
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"prod": _make_cluster_config(credentials=creds, jmx_credentials=jmx_creds)},
            metadata={"prod": ClusterMetadata(source="static")},
        )

        result = list_all_clusters(expose_credentials=False)

        view = result[0]
        assert view.has_credentials is True
        assert view.has_jmx_credentials is True
        assert view.credentials is None
        assert view.jmx_credentials is None

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_masks_additional_kwargs(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = _make_cassanova_config(
            clusters={
                "prod": _make_cluster_config(
                    additional_kwargs={"ssl_options": {"ca_certs": "/path/to/ca.crt"}}
                )
            },
            metadata={"prod": ClusterMetadata(source="static")},
        )

        result = list_all_clusters()

        view = result[0]
        assert view.has_additional_kwargs is True
        raw = view.model_dump()
        assert "ssl_options" not in str(raw)
        assert "ca_certs" not in str(raw)

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_no_credentials_reflected_correctly(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"anon": _make_cluster_config()},
            metadata={"anon": ClusterMetadata(source="static")},
        )

        result = list_all_clusters()

        assert result[0].has_credentials is False
        assert result[0].has_jmx_credentials is False
        assert result[0].has_additional_kwargs is False

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_returns_both_static_and_k8s_clusters(self, mock_get_config: MagicMock) -> None:
        now = datetime.now(UTC)
        mock_get_config.return_value = _make_cassanova_config(
            clusters={
                "static-one": _make_cluster_config(),
                "k8s-one": _make_cluster_config(contact_points=["10.1.1.1"]),
            },
            metadata={
                "static-one": ClusterMetadata(source="static"),
                "k8s-one": ClusterMetadata(source="k8s", context="ctx", last_seen=now),
            },
        )

        result = list_all_clusters()

        sources = {r.name: r.source for r in result}
        assert sources["static-one"] == "static"
        assert sources["k8s-one"] == "k8s"

    @patch("cassanova.api.routes.api.admin_routes.get_clusters_config")
    def test_cluster_without_metadata_defaults_to_static(self, mock_get_config: MagicMock) -> None:
        mock_get_config.return_value = _make_cassanova_config(
            clusters={"orphan": _make_cluster_config()},
            metadata={},
        )

        result = list_all_clusters()

        assert result[0].source == "static"
        assert result[0].context is None
        assert result[0].last_seen is None
        assert result[0].miss_count == 0
