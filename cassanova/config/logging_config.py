import logging
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


class FileHandlerConfig(BaseModel):
    dir: str = Field(default="logs")
    max_bytes: int = Field(default=_MAX_BYTES)
    backup_count: int = Field(default=_BACKUP_COUNT)


class LoggerConfig(BaseModel):
    handlers: list[Literal["stdout", "file"]] = Field(default=["stdout"])
    file: FileHandlerConfig = FileHandlerConfig()


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    app: LoggerConfig = LoggerConfig()
    audit: LoggerConfig = LoggerConfig()


def configure_logging(config: LoggingConfig | None = None) -> None:
    config = config or LoggingConfig()
    level = getattr(logging, config.level.upper(), logging.INFO)

    _configure_root_logger(level, config.app)
    _configure_audit_logger(config.audit)


def _configure_root_logger(level: int, cfg: LoggerConfig) -> None:
    root = logging.getLogger("cassanova")
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if "stdout" in cfg.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(fmt)
        root.addHandler(handler)

    if "file" in cfg.handlers:
        log_dir = Path(cfg.file.dir)
        log_dir.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "cassanova.log", maxBytes=cfg.file.max_bytes, backupCount=cfg.file.backup_count
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)


def _configure_audit_logger(cfg: LoggerConfig) -> None:
    audit = logging.getLogger("cassanova.audit")
    audit.setLevel(logging.INFO)
    audit.propagate = False

    json_fmt = logging.Formatter("%(message)s")

    if "stdout" in cfg.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(json_fmt)
        audit.addHandler(handler)

    if "file" in cfg.handlers:
        log_dir = Path(cfg.file.dir)
        log_dir.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "audit.log", maxBytes=cfg.file.max_bytes, backupCount=cfg.file.backup_count
        )
        handler.setFormatter(json_fmt)
        audit.addHandler(handler)
