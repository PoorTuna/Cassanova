from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from cassanova.config.app_config import APPConfig
from cassanova.consts.app_routers import APPConsts
from cassanova.exceptions.route_handlers.auth_handler import add_auth_exception_handler
from cassanova.exceptions.route_handlers.cluster_unavailable_handler import add_cluster_unavailable_exceptions
from cassanova.exceptions.route_handlers.default_handler import add_default_exceptions
from cassanova.exceptions.route_handlers.not_found_handler import add_notfound_exceptions
from cassanova.exceptions.route_handlers.system_views_unavailable_handler import \
    add_system_views_unavailable_exception_handler
from cassanova.middleware.auth_middleware import AuthMiddleware


def bootstrap_app(app: FastAPI, app_config: APPConfig):
    __load_static_files(app)
    app.add_middleware(AuthMiddleware)
    __add_routers(app, app_config.routers)
    __add_exception_handlers(app)

    @app.on_event("shutdown")
    def shutdown_event():
        from cassanova.core.db.session_manager import session_manager
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
