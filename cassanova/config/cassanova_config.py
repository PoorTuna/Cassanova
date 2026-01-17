import os
from functools import cache
from logging import getLogger
from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, JsonConfigSettingsSource, SettingsConfigDict

from cassanova.config.app_config import APPConfig
from cassanova.config.auth_config import AuthConfig
from cassanova.config.cluster_config import ClusterConnectionConfig

logger = getLogger(__name__)


class CassanovaConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file='.env', env_file_encoding='utf-8',
                                      extra='ignore')

    clusters: dict[str, ClusterConnectionConfig] = {}
    auth: AuthConfig = AuthConfig()
    app_config: APPConfig = APPConfig()

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


@cache
def get_clusters_config(*args, **kwargs):
    return CassanovaConfig(*args, **kwargs)
