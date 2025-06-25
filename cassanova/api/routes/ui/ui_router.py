from fastapi import APIRouter

from cassanova.api.routes.ui.dashboard_routes import cassanova_ui_dashboard_router
from cassanova.api.routes.ui.operations_routes import cassanova_ui_operations_router


def get_cassanova_ui_router() -> APIRouter:
    cassanova_ui_router = APIRouter(tags=["UI"])
    cassanova_ui_router.include_router(cassanova_ui_dashboard_router)
    cassanova_ui_router.include_router(cassanova_ui_operations_router)

    return cassanova_ui_router
