from logging import getLogger

from fastapi import FastAPI
from kubernetes import client, config as k8s_config
from starlette.staticfiles import StaticFiles

from cassanova.config.app_config import APPConfig
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.consts.app_routers import APPConsts
from cassanova.core.session_manager import session_manager
from cassanova.api.exception_handlers.auth_handler import add_auth_exception_handler
from cassanova.api.exception_handlers.cluster_unavailable_handler import add_cluster_unavailable_exceptions
from cassanova.api.exception_handlers.default_handler import add_default_exceptions
from cassanova.api.exception_handlers.not_found_handler import add_notfound_exceptions
from cassanova.api.exception_handlers.system_views_unavailable_handler import \
    add_system_views_unavailable_exception_handler
from cassanova.middleware.auth_middleware import AuthMiddleware

logger = getLogger(__name__)


def bootstrap_app(app: FastAPI, app_config: APPConfig):
    __load_static_files(app)
    __setup_tls_middleware(app, app_config.tls)
    app.add_middleware(AuthMiddleware)
    __add_routers(app, app_config.routers)
    __add_exception_handlers(app)
    __setup_k8s_clients(app)

    @app.on_event("shutdown")
    def shutdown_event():
        session_manager.shutdown_all()


def __add_routers(app: FastAPI, routers: list[str]):
    for router in routers:
        if router := APPConsts.AVAILABLE_ROUTER_MAPPING.get(router):
            app.include_router(router)


def __load_static_files(app: FastAPI):
    app.mount("/static", StaticFiles(directory="web/static"), name="static")


def __add_exception_handlers(app: FastAPI):
    add_default_exceptions(app)
    add_notfound_exceptions(app)
    add_cluster_unavailable_exceptions(app)
    add_system_views_unavailable_exception_handler(app)
    add_auth_exception_handler(app)


def __setup_tls_middleware(app: FastAPI, tls_config):
    if not tls_config.enabled:
        return
    
    from cassanova.middleware.tls_middleware import (
        HTTPSRedirectMiddleware,
        HSTSMiddleware,
        SecureCookieMiddleware
    )
    
    app.add_middleware(SecureCookieMiddleware)
    
    if tls_config.hsts_enabled:
        app.add_middleware(
            HSTSMiddleware,
            max_age=tls_config.hsts_max_age,
            include_subdomains=tls_config.hsts_include_subdomains
        )
    
    if tls_config.enforce_https:
        app.add_middleware(HTTPSRedirectMiddleware)
    
    logger.info(f"TLS middleware configured (HSTS: {tls_config.hsts_enabled}, Redirect: {tls_config.enforce_https})")


def __setup_k8s_clients(app: FastAPI):
    config = get_clusters_config()

    if not config.k8s.enabled:
        return

    @app.on_event("startup")
    def init_k8s_clients():
        try:
            if config.k8s.kubeconfig:
                k8s_config.load_kube_config(config_file=config.k8s.kubeconfig)
            else:
                try:
                    k8s_config.load_incluster_config()
                except k8s_config.ConfigException:
                    k8s_config.load_kube_config()

            app.state.k8s_core = client.CoreV1Api()
            app.state.k8s_custom = client.CustomObjectsApi()

        except Exception as e:
            logger.error(f"Failed to initialize K8s clients: {e}")

