from unittest.mock import patch

import pytest

from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection
from cassanova.config.timeouts_config import TimeoutConfig


class TestTimeoutConfigDefaults:
    def test_defaults_are_positive(self):
        timeouts = TimeoutConfig()
        assert timeouts.default_query > 0
        assert timeouts.connect > 0
        assert timeouts.ddl > 0
        assert timeouts.batch > 0
        assert timeouts.health_check > 0

    def test_default_query_under_ddl(self):
        timeouts = TimeoutConfig()
        assert timeouts.default_query <= timeouts.ddl
        assert timeouts.default_query <= timeouts.batch

    def test_rejects_non_positive_values(self):
        with pytest.raises(ValueError):
            TimeoutConfig(default_query=0)
        with pytest.raises(ValueError):
            TimeoutConfig(connect=-1)


class TestGenerateClusterConnectionTimeouts:
    def _make_config(self):
        return ClusterConnectionConfig(contact_points=["127.0.0.1"], port=9042)

    @patch("cassanova.config.cluster_config.Cluster")
    def test_passes_connect_timeout_when_timeouts_provided(self, mock_cluster):
        timeouts = TimeoutConfig(connect=7.5)
        generate_cluster_connection(self._make_config(), timeouts)

        kwargs = mock_cluster.call_args.kwargs
        assert kwargs["connect_timeout"] == 7.5

    @patch("cassanova.config.cluster_config.Cluster")
    def test_omits_connect_timeout_when_no_timeouts(self, mock_cluster):
        generate_cluster_connection(self._make_config(), None)

        kwargs = mock_cluster.call_args.kwargs
        assert "connect_timeout" not in kwargs

    @patch("cassanova.config.cluster_config.Cluster")
    def test_additional_kwargs_override_takes_precedence(self, mock_cluster):
        config = ClusterConnectionConfig(
            contact_points=["127.0.0.1"], additional_kwargs={"connect_timeout": 99}
        )
        generate_cluster_connection(config, TimeoutConfig(connect=10))

        kwargs = mock_cluster.call_args.kwargs
        assert kwargs["connect_timeout"] == 99
