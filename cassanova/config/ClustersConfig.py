import os
from functools import cache
from json import dump
from logging import getLogger
from pathlib import Path
from typing import Any

from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, JsonConfigSettingsSource

logger = getLogger(__name__)


class ClusterConfig(BaseModel):
    contact_points: list[str]
    username: str = Field()
    password: str = Field()
    additional_kwargs: dict[str, Any] = Field(default_factory=dict)


class ClustersConfig(BaseSettings):
    clusters: list[ClusterConfig]

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


def save_settings_to_file(settings: ClustersConfig, path: str | Path = os.getenv("CASSANOVA_CONFIG_PATH")) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        dump(settings.model_dump(), f, indent=4)


@cache
def get_clusters_config(*args, **kwargs):
    return ClustersConfig(*args, **kwargs)
