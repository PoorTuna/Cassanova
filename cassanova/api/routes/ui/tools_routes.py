from fastapi import HTTPException, APIRouter
from fastapi.requests import Request

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection
from cassanova.consts.cass_tools import CassTools
from cassanova.web.template_config import templates

clusters_config = get_clusters_config()
cassanova_ui_tools_router = APIRouter(tags=['UI'])


@cassanova_ui_tools_router.get("/cluster/{cluster_name}/tools/cqlsh")
def cqlsh_devtools(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()

    return templates.TemplateResponse("cqlsh.html", {
        "request": request,
        "cluster_config_entry": cluster_name,
        "cluster_name": cluster.metadata.cluster_name,
    })


@cassanova_ui_tools_router.get("/tools")
def tool_hub(request: Request):
    return templates.TemplateResponse("tools.html", {
        "request": request,
        "tools": sorted(CassTools.ALLOWED_TOOLS),
    })
