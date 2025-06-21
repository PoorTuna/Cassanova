from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from cassanova.config.APPConfig import APPConfig
from cassanova.consts.app_routers import APPConsts


def bootstrap_app(app: FastAPI, app_config: APPConfig):
    __load_static_files(app)
    __add_routers(app, app_config.routers)


def __add_routers(app: FastAPI, routers: list[str]):
    for router in routers:
        if router := APPConsts.AVAILABLE_ROUTER_MAPPING.get(router):
            app.include_router(router)


def __load_static_files(app: FastAPI):
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
