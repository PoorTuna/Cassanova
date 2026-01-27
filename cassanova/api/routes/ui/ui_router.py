from fastapi import APIRouter, Depends

from cassanova.api.dependencies.auth import require_web_user
from cassanova.api.routes.ui.dashboard_routes import cassanova_ui_dashboard_router
from cassanova.api.routes.ui.login_routes import login_router
from cassanova.api.routes.ui.node_recovery_routes import node_recovery_ui_router
from cassanova.api.routes.ui.tools_routes import cassanova_ui_tools_router


def get_cassanova_ui_router() -> APIRouter:
    cassanova_ui_router = APIRouter(tags=["UI"])
    cassanova_ui_router.include_router(login_router)
    cassanova_ui_router.include_router(
        cassanova_ui_dashboard_router,
        dependencies=[Depends(require_web_user)]
    )
    cassanova_ui_router.include_router(
        cassanova_ui_tools_router,
        dependencies=[Depends(require_web_user)]
    )
    cassanova_ui_router.include_router(
        node_recovery_ui_router,
        dependencies=[Depends(require_web_user)]
    )

    return cassanova_ui_router
