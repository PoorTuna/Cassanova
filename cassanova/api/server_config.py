import logging
from typing import Dict, Any

from cassanova.config.app_config import APPConfig

logger = logging.getLogger(__name__)


def build_uvicorn_config(app, app_config: APPConfig) -> Dict[str, Any]:
    config = {
        "app": app,
        "host": app_config.host,
        "port": app_config.port
    }
    
    if app_config.tls.enabled:
        _configure_tls(config, app_config)
    else:
        logger.info(f"TLS disabled - HTTP on {app_config.host}:{app_config.port}")
    
    return config


def _configure_tls(config: Dict[str, Any], app_config: APPConfig):
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
