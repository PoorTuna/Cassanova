from cassanova.api.routes.api.api_router import get_cassanova_api_router
from cassanova.api.routes.ui.dashboard_routes import cassanova_ui_dashboard_router
from cassanova.api.routes.ui.ui_router import get_cassanova_ui_router


class APPConsts:
    AVAILABLE_ROUTER_MAPPING = {
        'cassanova_ui_router': get_cassanova_ui_router(),
        'cassanova_api_router': get_cassanova_api_router(),
    }
