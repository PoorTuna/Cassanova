import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydantic import BaseModel, Field

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


class LogHandlerConfig(BaseModel):
    stdout: bool = Field(default=True)
    file: bool = Field(default=False)


class LoggingConfig(BaseModel):
    log_dir: str = Field(default="logs")
    level: str = Field(default="INFO")
    app: LogHandlerConfig = LogHandlerConfig()
    audit: LogHandlerConfig = LogHandlerConfig()


def configure_logging(config: LoggingConfig | None = None) -> None:
    config = config or LoggingConfig()
    log_dir = Path(config.log_dir)
    level = getattr(logging, config.level.upper(), logging.INFO)

    if config.app.file or config.audit.file:
        log_dir.mkdir(exist_ok=True)

    _configure_root_logger(log_dir, level, config.app)
    _configure_audit_logger(log_dir, config.audit)


def _configure_root_logger(log_dir: Path, level: int, handler_config: LogHandlerConfig) -> None:
    root = logging.getLogger("cassanova")
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if handler_config.stdout:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(fmt)
        root.addHandler(stdout)

    if handler_config.file:
        file_handler = RotatingFileHandler(
            log_dir / "cassanova.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


def _configure_audit_logger(log_dir: Path, handler_config: LogHandlerConfig) -> None:
    audit = logging.getLogger("cassanova.audit")
    audit.setLevel(logging.INFO)
    audit.propagate = False

    json_fmt = logging.Formatter("%(message)s")

    if handler_config.stdout:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(json_fmt)
        audit.addHandler(stdout)

    if handler_config.file:
        file_handler = RotatingFileHandler(
            log_dir / "audit.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
        )
        file_handler.setFormatter(json_fmt)
        audit.addHandler(file_handler)
