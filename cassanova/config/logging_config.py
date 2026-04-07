import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path("logs")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5


def configure_logging() -> None:
    _LOG_DIR.mkdir(exist_ok=True)

    _configure_root_logger()
    _configure_audit_logger()


def _configure_root_logger() -> None:
    root = logging.getLogger("cassanova")
    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(fmt)
    root.addHandler(stdout)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "cassanova.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def _configure_audit_logger() -> None:
    audit = logging.getLogger("cassanova.audit")
    audit.setLevel(logging.INFO)
    audit.propagate = False

    json_fmt = logging.Formatter("%(message)s")

    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(json_fmt)
    audit.addHandler(stdout)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "audit.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT
    )
    file_handler.setFormatter(json_fmt)
    audit.addHandler(file_handler)
