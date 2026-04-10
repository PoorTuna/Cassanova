import logging
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydantic import BaseModel, Field

from cassanova.config._json_log_formatter import JsonFormatter

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


class FileHandlerConfig(BaseModel):
    dir: str = Field(default="logs")
    max_bytes: int = Field(default=_MAX_BYTES)
    backup_count: int = Field(default=_BACKUP_COUNT)


class LoggerConfig(BaseModel):
    handlers: list[str] = Field(default=["stdout"])
    file: FileHandlerConfig = FileHandlerConfig()


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")
    app: LoggerConfig = LoggerConfig()
    audit: LoggerConfig = LoggerConfig()


def _build_stdout_handler(fmt: logging.Formatter, _cfg: LoggerConfig) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    return handler


def _build_file_handler(
    fmt: logging.Formatter, cfg: LoggerConfig, filename: str
) -> logging.Handler:
    log_dir = Path(cfg.file.dir)
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / filename, maxBytes=cfg.file.max_bytes, backupCount=cfg.file.backup_count
    )
    handler.setFormatter(fmt)
    return handler


def configure_logging(config: LoggingConfig | None = None) -> None:
    config = config or LoggingConfig()
    level = getattr(logging, config.level.upper(), logging.INFO)

    _configure_logger(
        "cassanova",
        level,
        config.app,
        JsonFormatter(),
        "cassanova.log",
    )
    _configure_logger(
        "cassanova.audit",
        logging.INFO,
        config.audit,
        logging.Formatter("%(message)s"),
        "audit.log",
        propagate=False,
    )


_HANDLER_FACTORIES: dict[str, Callable[..., logging.Handler]] = {
    "stdout": lambda fmt, cfg, _fn: _build_stdout_handler(fmt, cfg),
    "file": lambda fmt, cfg, fn: _build_file_handler(fmt, cfg, fn),
}


def _configure_logger(
    name: str,
    level: int,
    cfg: LoggerConfig,
    fmt: logging.Formatter,
    filename: str,
    propagate: bool = True,
) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    for handler_name in cfg.handlers:
        factory = _HANDLER_FACTORIES.get(handler_name)
        if factory:
            logger.addHandler(factory(fmt, cfg, filename))
