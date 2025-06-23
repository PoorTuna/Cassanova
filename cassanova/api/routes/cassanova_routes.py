from datetime import datetime

from cassandra.cluster import Session
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from cassanova.cass.constructors.cluster_info import generate_cluster_info
from cassanova.cass.constructors.keyspaces import generate_keyspaces_info
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection

clusters_config = get_clusters_config()
cassanova_router = APIRouter(tags=["UI"])
templates = Jinja2Templates(directory="web/templates")


@cassanova_router.get('/')
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'clusters': clusters_config.clusters})


@cassanova_router.get("/cluster/{cluster_name}")
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


@cassanova_router.get("/cluster/{cluster_name}/keyspace/{keyspace_name}")
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
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })
