from fastapi import APIRouter

from cassanova.api.routes.api.delete_api_routes import cassanova_api_deleter_router
from cassanova.api.routes.api.get_api_routes import cassanova_api_getter_router
from cassanova.api.routes.api.post_api_routes import cassanova_api_post_router


def get_cassanova_api_router() -> APIRouter:
    cassanova_api_router = APIRouter(prefix='/api/v1', tags=["API"])
    cassanova_api_router.include_router(cassanova_api_deleter_router)
    cassanova_api_router.include_router(cassanova_api_getter_router)
    cassanova_api_router.include_router(cassanova_api_post_router)


    return cassanova_api_router
