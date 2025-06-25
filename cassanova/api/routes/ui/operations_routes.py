from fastapi import HTTPException, APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection

clusters_config = get_clusters_config()
templates = Jinja2Templates(directory="web/templates")
cassanova_ui_operations_router = APIRouter(tags=['UI'])


@cassanova_ui_operations_router.get("/cluster/{cluster_name}/operations")
def operations_hub(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()

    return templates.TemplateResponse("operations.html", {
        "request": request,
        "cluster_config_entry": cluster_name,
        "cluster_name": cluster.metadata.cluster_name,
    })

@cassanova_ui_operations_router.get("/cluster/{cluster_name}/operations/cqlsh")
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
