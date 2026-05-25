from asyncio import create_task, sleep, to_thread
from datetime import UTC, datetime
from logging import getLogger

from fastapi import FastAPI
from kubernetes import client
from kubernetes import config as k8s_config
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from cassanova.api.exception_handlers.auth_handler import add_auth_exception_handler
from cassanova.api.exception_handlers.cluster_unavailable_handler import (
    add_cluster_unavailable_exceptions,
)
from cassanova.api.exception_handlers.cql_handler import add_cql_exception_handlers
from cassanova.api.exception_handlers.default_handler import add_default_exceptions
from cassanova.api.exception_handlers.not_found_handler import add_notfound_exceptions
from cassanova.api.exception_handlers.system_views_unavailable_handler import (
    add_system_views_unavailable_exception_handler,
)
from cassanova.config.app_config import APPConfig
from cassanova.config.cassanova_config import CassanovaConfig, get_clusters_config
from cassanova.config.cluster_metadata import ClusterMetadata
from cassanova.config.tls_config import TLSConfig
from cassanova.consts.app_routers import APPConsts
from cassanova.core.k8s_discovery import DiscoveredCluster, discover_k8s_clusters
from cassanova.core.session_manager import session_manager
from cassanova.middleware.auth_middleware import AuthMiddleware
from cassanova.middleware.tls_middleware import (
    HSTSMiddleware,
    HTTPSRedirectMiddleware,
    SecureCookieMiddleware,
)

logger = getLogger(__name__)

_STATIC_CACHE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


class CachedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = f"public, max-age={_STATIC_CACHE_MAX_AGE}"
        return response


def bootstrap_app(app: FastAPI, app_config: APPConfig) -> None:
    __load_static_files(app)
    __setup_tls_middleware(app, app_config.tls)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    __add_routers(app, app_config.routers)
    __add_exception_handlers(app)
    __setup_k8s_clients(app)
    __warn_insecure_secret()

    @app.on_event("shutdown")
    def shutdown_event() -> None:
        session_manager.shutdown_all()


def __add_routers(app: FastAPI, routers: list[str]) -> None:
    for router in routers:
        if router := APPConsts.AVAILABLE_ROUTER_MAPPING.get(router):  # type: ignore[assignment]
            app.include_router(router)


def __load_static_files(app: FastAPI) -> None:
    _build_css_bundle()
    app.mount("/static", CachedStaticFiles(directory="web/static"), name="static")


def _build_css_bundle() -> None:
    try:
        from cassanova.web.build_css import build
        build()
    except Exception as e:
        logger.warning(f"CSS bundle build failed, falling back to unbundled: {e}")


def __add_exception_handlers(app: FastAPI) -> None:
    add_default_exceptions(app)
    add_notfound_exceptions(app)
    add_cluster_unavailable_exceptions(app)
    add_system_views_unavailable_exception_handler(app)
    add_auth_exception_handler(app)
    add_cql_exception_handlers(app)


def __setup_tls_middleware(app: FastAPI, tls_config: TLSConfig) -> None:
    if not tls_config.enabled:
        return

    app.add_middleware(SecureCookieMiddleware)

    if tls_config.hsts_enabled:
        app.add_middleware(
            HSTSMiddleware,
            max_age=tls_config.hsts_max_age,
            include_subdomains=tls_config.hsts_include_subdomains,
        )

    if tls_config.enforce_https:
        app.add_middleware(HTTPSRedirectMiddleware)

    logger.info(
        f"TLS middleware configured"
        f" (HSTS: {tls_config.hsts_enabled},"
        f" Redirect: {tls_config.enforce_https})"
    )


def __warn_insecure_secret() -> None:
    config = get_clusters_config()
    if config.auth.enabled and config.auth.secret_key == "insecure_default_secret_change_me":
        logger.warning(
            "AUTH SECRET KEY IS SET TO THE DEFAULT INSECURE VALUE. "
            "Change 'secret_key' in your auth configuration before deploying to production."
        )


def __setup_k8s_clients(app: FastAPI) -> None:
    config = get_clusters_config()

    if not config.k8s.enabled:
        return

    @app.on_event("startup")
    def init_k8s_clients() -> None:
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

            if config.k8s.periodic_discovery_enabled:
                app.state.discovery_task = create_task(run_periodic_discovery(config))

        except Exception as e:
            logger.error(f"Failed to initialize K8s clients: {e}")


async def run_periodic_discovery(config: CassanovaConfig) -> None:
    logger.info(
        f"Starting periodic K8s discovery every {config.k8s.discovery_interval_seconds} seconds"
    )
    while True:
        try:
            await sleep(config.k8s.discovery_interval_seconds)
            await to_thread(_run_discovery_pass, config)
        except Exception as e:
            logger.error(f"Unhandled error in periodic discovery loop: {e}")


def _run_discovery_pass(config: CassanovaConfig) -> None:
    try:
        discovered = discover_k8s_clusters(
            config.k8s.kubeconfig,
            config.k8s.namespace,
            config.k8s.suffix,
            config.k8s.contexts,
            config.k8s.external_only,
            config.k8s.cluster_include,
            config.k8s.cluster_exclude,
        )
    except Exception as e:
        logger.error(f"K8s discovery FAILED — skipping miss accounting: {e}")
        return

    now = datetime.now(UTC)
    new_clusters = dict(config.clusters)
    new_meta = dict(config.cluster_metadata)

    _merge_discovered_clusters(discovered, new_clusters, new_meta, now)
    _evict_stale_clusters(new_clusters, new_meta, discovered, config.k8s.stale_threshold)

    config.clusters = new_clusters
    config.cluster_metadata = new_meta


def _merge_discovered_clusters(
    discovered: dict[str, DiscoveredCluster],
    clusters: dict,
    metadata: dict,
    now: datetime,
) -> None:
    for name, dc in discovered.items():
        if name not in clusters:
            logger.info(f"New cluster discovered: {name}")
            clusters[name] = dc.config

        existing = metadata.get(name)
        metadata[name] = ClusterMetadata(
            source="k8s",
            context=dc.context,
            discovered_at=existing.discovered_at if existing else now,
            last_seen=now,
            miss_count=0,
        )


def _evict_stale_clusters(
    clusters: dict,
    metadata: dict,
    discovered: dict[str, DiscoveredCluster],
    stale_threshold: int,
) -> None:
    for name in list(metadata):
        meta = metadata[name]
        if meta.source != "k8s" or name in discovered:
            continue

        new_miss_count = meta.miss_count + 1
        logger.debug(f"Cluster '{name}' missed scan ({new_miss_count}/{stale_threshold})")

        if new_miss_count >= stale_threshold:
            logger.warning(
                f"Evicting stale k8s cluster '{name}' "
                f"(missed {new_miss_count} consecutive scans)"
            )
            clusters.pop(name, None)
            metadata.pop(name, None)
            session_manager.shutdown(name)
        else:
            metadata[name] = ClusterMetadata(
                source=meta.source,
                context=meta.context,
                discovered_at=meta.discovered_at,
                last_seen=meta.last_seen,
                miss_count=new_miss_count,
            )
