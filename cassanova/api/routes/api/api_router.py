from fastapi import APIRouter

from cassanova.api.routes.api.auth_routes import auth_router
from cassanova.api.routes.api.cluster_routes import cluster_router
from cassanova.api.routes.api.query_routes import query_router


def get_cassanova_api_router() -> APIRouter:
    cassanova_api_router = APIRouter(prefix='/api/v1', tags=["API"])
    cassanova_api_router.include_router(cluster_router)
    cassanova_api_router.include_router(query_router)
    cassanova_api_router.include_router(auth_router)

    return cassanova_api_router
