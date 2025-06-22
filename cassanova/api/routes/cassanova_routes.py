from datetime import datetime

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from cassanova.cass.get_cluster_description import get_cluster_description
from cassanova.cass.get_cluster_health import get_cluster_health
from cassanova.cass.get_cluster_size import get_total_cluster_size_estimate
from cassanova.cass.get_topology_details import get_topology_details
from cassanova.config.CassanovaConfig import get_clusters_config
from cassanova.config.ClusterConfig import ClusterConfig
from cassanova.models.ClusterInfo import Table, Keyspace, Node, ClusterInfo

clusters_config = get_clusters_config()
cassanova_router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@cassanova_router.get('/')
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'clusters': clusters_config.clusters})


@cassanova_router.get("/cluster/{cluster_name}")
async def cluster_dashboard(request: Request, cluster_name: str):
    cluster_config: ClusterConfig = clusters_config.clusters.get(cluster_name, None)
    if cluster_config is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = Cluster(contact_points=cluster_config.contact_points, port=cluster_config.port,
                      auth_provider=PlainTextAuthProvider(username=cluster_config.username,
                                                          password=cluster_config.password),
                      **cluster_config.additional_kwargs
                      )  # todo: cache this
    cluster_session: Session = cluster.connect()
    cluster_metadata = cluster.metadata
    keyspaces = cluster_metadata.keyspaces
    cluster_description = get_cluster_description(cluster_session)
    cluster_health = get_cluster_health(cluster)
    topology_details = get_topology_details(cluster)

    cluster_info = ClusterInfo(
        **cluster_description,
        **cluster_health,
        **topology_details,
        cluster_size=get_total_cluster_size_estimate(cluster_session),
        version='5.0.4',
        nodes=[
            Node(name="node1", status="Up", load="4.2 GB", cpu_percent=18.5, ram_percent=72.3, token_range="0 - 10000"),
        ],
        keyspaces=[
            Keyspace(
                name=name,
                replication=metadata.replication_strategy.export_for_schema() if metadata.replication_strategy else "N/A",
                virtual=metadata.virtual,
                durable_writes=metadata.durable_writes,
                tables=[Table(name=table) for table in metadata.tables]
            ) for name, metadata in list(keyspaces.items())
        ]
    )  # todo: export into different functions
    current_year = datetime.now().year
    return templates.TemplateResponse("cluster.html", {
        "request": request,
        "cluster": cluster_info,
        "cluster_config_entry": cluster_name,
        "current_year": current_year
    })
