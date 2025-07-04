from datetime import datetime

from cassandra.cluster import Session
from fastapi import HTTPException, APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from cassanova.api.routes.api.get_api_routes import get_node_status
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection
from cassanova.core.constructors.cluster_info import generate_cluster_info
from cassanova.core.constructors.keyspaces import generate_keyspaces_info

clusters_config = get_clusters_config()
templates = Jinja2Templates(directory="web/templates")
cassanova_ui_dashboard_router = APIRouter(tags=['UI'])


@cassanova_ui_dashboard_router.get('/')
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'clusters': clusters_config.clusters})


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}")
async def cluster_dashboard(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    session: Session = cluster.connect()
    cluster_info = generate_cluster_info(cluster, session)
    current_year = datetime.now().year
    return templates.TemplateResponse("cluster.html", {
        "request": request,
        "cluster": cluster_info,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
async def keyspace_dashboard(request: Request, cluster_name: str, keyspace_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspace_info = generate_keyspaces_info([(keyspace_name, cluster.metadata.keyspaces.get(keyspace_name))])[0]

    current_year = datetime.now().year
    return templates.TemplateResponse("keyspace.html", {
        "request": request,
        "keyspace": keyspace_info,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/nodes")
async def nodes_dashboard(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    nodetool_status_info = await get_node_status(cluster_name)

    current_year = datetime.now().year
    return templates.TemplateResponse("nodes.html", {
        "request": request,
        "nodetool_status": nodetool_status_info,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/settings")
def cluster_settings(request: Request, cluster_name: str):
    cluster_config = clusters_config.clusters.get(cluster_name)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    session = cluster.connect()

    try:
        rows = session.execute("SELECT * FROM system_views.settings")
        settings_dict = {row.name: row.value for row in rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query settings: {e}")
    finally:
        session.shutdown()

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "cluster_settings": settings_dict  # pass dict directly
    })
