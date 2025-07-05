import os
from functools import cache
from json import dump
from logging import getLogger
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, JsonConfigSettingsSource

from cassanova.config.app_config import APPConfig
from cassanova.config.cluster_config import ClusterConnectionConfig

logger = getLogger(__name__)


# todo: add support for env vars injection + env files as an alternative to the file loading
class CassanovaConfig(BaseSettings):
    clusters: dict[str, ClusterConnectionConfig]
    monitoring_url: Optional[str] = None
    app_config: APPConfig

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_path = os.getenv("CASSANOVA_CONFIG_PATH")
        if not config_path:
            raise ValueError("CASSANOVA_CONFIG_PATH environment variable is not set.")
        return (JsonConfigSettingsSource(settings_cls, json_file=config_path),)


def save_settings_to_file(settings: CassanovaConfig, path: str | Path = os.getenv("CASSANOVA_CONFIG_PATH")) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        dump(settings.model_dump(), f, indent=4)


@cache
def get_clusters_config(*args, **kwargs):
    return CassanovaConfig(*args, **kwargs)
