from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from cassanova.api.exceptions.cluster_not_available import add_cluster_unavailable_exceptions
from cassanova.api.exceptions.default_handler import add_default_exceptions
from cassanova.api.exceptions.not_found_handler import add_not_found_exceptions
from cassanova.config.app_config import APPConfig
from cassanova.consts.app_routers import APPConsts


def bootstrap_app(app: FastAPI, app_config: APPConfig):
    __load_static_files(app)
    __add_routers(app, app_config.routers)
    __add_exception_handlers(app)


def __add_routers(app: FastAPI, routers: list[str]):
    for router in routers:
        if router := APPConsts.AVAILABLE_ROUTER_MAPPING.get(router):
            app.include_router(router)


def __load_static_files(app: FastAPI):
    app.mount("/static", StaticFiles(directory="web/static"), name="static")


def __add_exception_handlers(app: FastAPI):
    add_default_exceptions(app)
    add_not_found_exceptions(app)
    add_cluster_unavailable_exceptions(app)