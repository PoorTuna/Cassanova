from datetime import datetime
from fastapi.templating import Jinja2Templates
from cassanova.config.cassanova_config import get_clusters_config
# Import late to avoid circular dep if needed, or check auth.py deps
from cassanova.api.dependencies.auth import check_permission

templates = Jinja2Templates(directory="web/templates")

def register_context_processors():
    """Register global context processors for all templates."""
    config = get_clusters_config()
    
    
    # Add current_year to globals
    templates.env.globals["current_year"] = datetime.now().year

    # RBAC Helper
    templates.env.globals["check_permission"] = check_permission

# Call it once at module level or during bootstrap
register_context_processors()
