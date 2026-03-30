import logging
import os
import sys
from typing import Any

from cassanova.config.app_config import APPConfig

logger = logging.getLogger(__name__)

_DEFAULT_WORKERS = min(os.cpu_count() or 1, 4)


def build_uvicorn_config(app: Any, app_config: APPConfig) -> dict[str, Any]:
    workers = _DEFAULT_WORKERS if sys.platform != "win32" else 1

    config: dict[str, Any] = {
        "app": "cassanova.run:app" if workers > 1 else app,
        "host": app_config.host,
        "port": app_config.port,
        "workers": workers,
        "timeout_keep_alive": 30,
    }

    if workers > 1:
        logger.info(f"Running with {workers} workers")
    else:
        logger.info("Running single worker (Windows or single-core)")

    if app_config.tls.enabled:
        _configure_tls(config, app_config)
    else:
        logger.info(f"TLS disabled - HTTP on {app_config.host}:{app_config.port}")

    return config


def _configure_tls(config: dict[str, Any], app_config: APPConfig) -> None:
    app_config.tls.validate_tls_files()

    config["ssl_keyfile"] = app_config.tls.key_file
    config["ssl_certfile"] = app_config.tls.cert_file

    if app_config.tls.ca_bundle:
        config["ssl_ca_certs"] = app_config.tls.ca_bundle

    if app_config.tls.min_tls_version == "TLSv1_3":
        config["ssl_version"] = 5
    else:
        config["ssl_version"] = 4

    config["ssl_ciphers"] = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"

    logger.info(
        f"TLS enabled - HTTPS on {app_config.host}:{app_config.port} "
        f"(min version: {app_config.tls.min_tls_version})"
    )
