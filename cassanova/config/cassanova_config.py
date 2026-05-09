import os
from datetime import UTC, datetime
from functools import cache
from logging import getLogger
from pathlib import Path
from typing import Any

from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from cassanova.config.app_config import APPConfig
from cassanova.config.auth_config import AuthConfig
from cassanova.config.cluster_config import ClusterConnectionConfig
from cassanova.config.cluster_metadata import ClusterMetadata
from cassanova.config.k8s_config import K8sConfig
from cassanova.config.logging_config import LoggingConfig
from cassanova.config.timeouts_config import TimeoutConfig

logger = getLogger(__name__)


class CassanovaConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    clusters: dict[str, ClusterConnectionConfig] = {}
    cluster_metadata: dict[str, ClusterMetadata] = {}
    auth: AuthConfig = AuthConfig()
    app_config: APPConfig = APPConfig()
    logging: LoggingConfig = LoggingConfig()
    k8s: K8sConfig = K8sConfig()
    timeouts: TimeoutConfig = TimeoutConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = [init_settings, env_settings, dotenv_settings]

        config_path = os.getenv("CASSANOVA_CONFIG_PATH")
        if config_path and Path(config_path).exists():
            sources.append(JsonConfigSettingsSource(settings_cls, json_file=config_path))

        return tuple(sources)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        for name in self.clusters:
            self.cluster_metadata.setdefault(name, ClusterMetadata(source="static"))

        if self.k8s.enabled:
            self._run_initial_k8s_discovery()

    def _run_initial_k8s_discovery(self) -> None:
        from cassanova.core.k8s_discovery import KubernetesDiscoveryError, discover_k8s_clusters

        logger.info("Starting K8s Service Discovery...")
        try:
            discovered = discover_k8s_clusters(
                kubeconfig_path=self.k8s.kubeconfig,
                namespace=self.k8s.namespace,
                service_suffix=self.k8s.suffix,
                contexts=self.k8s.contexts,
                external_only=self.k8s.external_only,
            )
        except KubernetesDiscoveryError as e:
            logger.error(f"K8s Discovery failed: {e}")
            return
        except Exception as e:
            logger.error(f"K8s Discovery failed unexpectedly: {e}")
            return

        if not discovered:
            return

        now = datetime.now(UTC)
        for name, dc in discovered.items():
            self.clusters[name] = dc.config
            self.cluster_metadata[name] = ClusterMetadata(
                source="k8s",
                context=dc.context,
                discovered_at=now,
                last_seen=now,
            )
        logger.info(
            f"K8s Discovery added {len(discovered)} clusters: {list(discovered.keys())}"
        )


@cache
def get_clusters_config(*args: Any, **kwargs: Any) -> CassanovaConfig:
    config = CassanovaConfig(*args, **kwargs)
    return config
