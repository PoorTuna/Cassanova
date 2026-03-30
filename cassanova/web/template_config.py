import time
from datetime import datetime

from fastapi.templating import Jinja2Templates

# Import late to avoid circular dep if needed, or check auth.py deps
from cassanova.api.dependencies.auth import check_permission
from cassanova.config.cassanova_config import get_clusters_config

templates = Jinja2Templates(directory="web/templates")


def register_context_processors() -> None:
    """Register global context processors for all templates."""
    config = get_clusters_config()

    templates.env.globals["current_year"] = datetime.now().year
    templates.env.globals["cache_bust"] = str(int(time.time()))
    templates.env.globals["node_recovery_enabled"] = config.k8s.node_recovery.enabled
    templates.env.globals["check_permission"] = check_permission
    def _get_cluster_keys() -> list[str]:
        return list(get_clusters_config().clusters.keys())

    templates.env.globals["get_cluster_keys"] = _get_cluster_keys


# Call it once at module level or during bootstrap
register_context_processors()
