import os
from functools import cache
from logging import getLogger
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, JsonConfigSettingsSource, SettingsConfigDict

from cassanova.config.app_config import APPConfig
from cassanova.config.auth_config import AuthConfig
from cassanova.config.cluster_config import ClusterConnectionConfig
from cassanova.config.k8s_config import K8sDiscoveryConfig

logger = getLogger(__name__)


class CassanovaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file='.env', env_file_encoding='utf-8',
                                      extra='ignore')

    clusters: dict[str, ClusterConnectionConfig] = {}
    auth: AuthConfig = AuthConfig()
    app_config: APPConfig = APPConfig()
    k8s: K8sDiscoveryConfig = K8sDiscoveryConfig()

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
        if self.k8s.enabled:
            from cassanova.core.k8s_discovery import discover_k8s_clusters
            logger.info("Starting K8s Service Discovery...")
            try:
                discovered = discover_k8s_clusters(
                    kubeconfig_path=self.k8s.kubeconfig,
                    namespace=self.k8s.namespace,
                    service_suffix=self.k8s.suffix
                )
                if discovered:
                    self.clusters.update(discovered)
                    logger.info(f"K8s Discovery added {len(discovered)} clusters: {list(discovered.keys())}")
            except Exception as e:
                logger.error(f"K8s Discovery failed: {e}")


@cache
def get_clusters_config(*args, **kwargs):
    config = CassanovaConfig(*args, **kwargs)
    return config
