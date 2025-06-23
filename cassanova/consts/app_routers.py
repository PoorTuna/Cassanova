from cassanova.api.routes.cassanova_api_routes import cassanova_api_router
from cassanova.api.routes.cassanova_routes import cassanova_router


class APPConsts:
    AVAILABLE_ROUTER_MAPPING = {
        'cassanova_router': cassanova_router,
        'cassanova_api_router': cassanova_api_router,
    }
