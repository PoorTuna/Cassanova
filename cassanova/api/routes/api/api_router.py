from fastapi import APIRouter, Depends

from cassanova.api.dependencies.auth import require_user
from cassanova.api.routes.api.auth_routes import auth_router
from cassanova.api.routes.api.cluster_routes import cluster_router
from cassanova.api.routes.api.data_routes import data_router
from cassanova.api.routes.api.query_routes import query_router


def get_cassanova_api_router() -> APIRouter:
    cassanova_api_router = APIRouter(prefix='/api/v1', tags=["API"])

    cassanova_api_router.include_router(cluster_router, dependencies=[Depends(require_user)])
    cassanova_api_router.include_router(query_router, dependencies=[Depends(require_user)])
    cassanova_api_router.include_router(data_router, dependencies=[Depends(require_user)])
    cassanova_api_router.include_router(auth_router, dependencies=[Depends(require_user)])

    return cassanova_api_router
