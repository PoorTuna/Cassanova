from datetime import datetime

from cassandra.cluster import Session
from fastapi import HTTPException, APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from cassanova.api.routes.api.get_api_routes import get_nodes, get_cluster_settings, get_cluster_vnodes
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
def cluster_dashboard(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = generate_cluster_connection(cluster_config)
    session: Session = cluster.connect()
    cluster_info = generate_cluster_info(cluster, session)
    current_year = datetime.now().year
    return templates.TemplateResponse("cluster.html", {
        "request": request,
        "monitoring_url": clusters_config.monitoring_url,
        "cluster": cluster_info,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
def keyspace_dashboard(request: Request, cluster_name: str, keyspace_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    keyspace_info = generate_keyspaces_info([(keyspace_name, cluster.metadata.keyspaces.get(keyspace_name))])[0]

    current_year = datetime.now().year
    return templates.TemplateResponse("keyspace.html", {
        "request": request,
        "monitoring_url": clusters_config.monitoring_url,
        "keyspace": keyspace_info,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/nodes")
def nodes_dashboard(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()
    nodes_info = get_nodes(cluster_name)

    current_year = datetime.now().year
    return templates.TemplateResponse("nodes.html", {
        "request": request,
        "monitoring_url": clusters_config.monitoring_url,
        "nodes": nodes_info,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/settings")
def cluster_settings(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()

    settings_dict = get_cluster_settings(cluster_name)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "monitoring_url": clusters_config.monitoring_url,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "cluster_settings": settings_dict,
    })


@cassanova_ui_dashboard_router.get("/cluster/{cluster_name}/vnodes")
def cluster_settings(request: Request, cluster_name: str):
    cluster_config: ClusterConnectionConfig = clusters_config.clusters.get(cluster_name, None)
    if not cluster_config:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster = generate_cluster_connection(cluster_config)
    cluster.connect()

    vnodes = get_cluster_vnodes(cluster_name).get('nodes')
    return templates.TemplateResponse("vnodes.html", {
        "request": request,
        "monitoring_url": clusters_config.monitoring_url,
        "cluster_name": cluster.metadata.cluster_name,
        "cluster_config_entry": cluster_name,
        "vnodes": vnodes,
    })
