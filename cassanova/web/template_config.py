from datetime import datetime
from fastapi.templating import Jinja2Templates
from cassanova.config.cassanova_config import get_clusters_config

templates = Jinja2Templates(directory="web/templates")

def register_context_processors():
    """Register global context processors for all templates."""
    config = get_clusters_config()
    
    # Add monitoring_url to globals
    templates.env.globals["monitoring_url"] = config.monitoring_url
    
    # Add current_year to globals
    templates.env.globals["current_year"] = datetime.now().year

# Call it once at module level or during bootstrap
register_context_processors()
