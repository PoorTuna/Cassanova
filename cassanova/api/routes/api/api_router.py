from fastapi import APIRouter, Depends

from cassanova.api.dependencies.auth import require_user, require_permission
from cassanova.api.routes.api.auth_routes import auth_router
from cassanova.api.routes.api.cluster_routes import cluster_router
from cassanova.api.routes.api.data_routes import data_router
from cassanova.api.routes.api.node_recovery_routes import node_recovery_router
from cassanova.api.routes.api.tools_routes import tools_router


def get_cassanova_api_router() -> APIRouter:
    cassanova_api_router = APIRouter(prefix='/api/v1', tags=["API"])

    cassanova_api_router.include_router(cluster_router, dependencies=[Depends(require_permission("cluster:view"))])
    cassanova_api_router.include_router(tools_router, dependencies=[Depends(require_user)])
    cassanova_api_router.include_router(data_router, dependencies=[Depends(require_permission("data:read"))])
    cassanova_api_router.include_router(auth_router, dependencies=[Depends(require_permission("cluster:admin"))])
    cassanova_api_router.include_router(node_recovery_router,
                                        dependencies=[Depends(require_permission("cluster:admin"))])

    return cassanova_api_router
