import base64
import os
from logging import getLogger
from typing import Optional

try:
    from kubernetes import client, config
    from kubernetes.client import ApiException

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

from cassanova.config.cluster_config import ClusterConnectionConfig, ClusterCredentials

logger = getLogger(__name__)


def discover_k8s_clusters(
        kubeconfig_path: Optional[str] = None,
        namespace: Optional[str] = None,
        service_suffix: str = "-service"
) -> dict[str, ClusterConnectionConfig]:
    if not K8S_AVAILABLE:
        logger.warning("Kubernetes package not installed. Skipping K8s discovery.")
        return {}

    if not _load_k8s_config(kubeconfig_path):
        return {}

    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()

    k8s_clusters = _fetch_k8ssandra_clusters(custom_api, namespace)
    if not k8s_clusters:
        return {}

    items = k8s_clusters.get("items", [])
    logger.info(f"Found {len(items)} K8ssandraClusters.")

    discovered_clusters = {}
    for item in items:
        _process_k8ssandra_cluster(item, core_api, namespace, service_suffix, discovered_clusters)

    return discovered_clusters


def _load_k8s_config(kubeconfig_path: Optional[str]) -> bool:
    try:
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
        return True
    except Exception as e:
        logger.error(f"Failed to load kubeconfig: {e}")
        return False


def _fetch_k8ssandra_clusters(custom_api, namespace: Optional[str]) -> Optional[dict]:
    try:
        if namespace:
            return custom_api.list_namespaced_custom_object(
                group="k8ssandra.io",
                version="v1alpha1",
                namespace=namespace,
                plural="k8ssandraclusters"
            )
        else:
            return custom_api.list_cluster_custom_object(
                group="k8ssandra.io",
                version="v1alpha1",
                plural="k8ssandraclusters"
            )
    except ApiException as e:
        if e.status == 404:
            logger.info("No K8ssandraCluster CRDs found.")
        else:
            logger.error(f"Error listing K8ssandraClusters: {e}")
        return None


def _process_k8ssandra_cluster(item: dict, core_api, namespace: Optional[str], 
                                service_suffix: str, discovered_clusters: dict):
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    cluster_name = metadata.get("name")
    cluster_namespace = metadata.get("namespace", "default")

    if not cluster_name:
        return

    credentials = _extract_cluster_credentials(core_api, cluster_name, cluster_namespace)
    datacenters = spec.get("cassandra", {}).get("datacenters", [])

    for dc in datacenters:
        _process_datacenter(dc, cluster_name, cluster_namespace, namespace, 
                           service_suffix, core_api, credentials, discovered_clusters)


def _extract_cluster_credentials(core_api, cluster_name: str, 
                                 cluster_namespace: str) -> Optional[ClusterCredentials]:
    secret_name = f"{cluster_name}-superuser"
    try:
        secret = core_api.read_namespaced_secret(secret_name, cluster_namespace)
        data = secret.data or {}
        username_b64 = data.get("username")
        password_b64 = data.get("password")

        if username_b64 and password_b64:
            username = base64.b64decode(username_b64).decode('utf-8')
            password = base64.b64decode(password_b64).decode('utf-8')
            return ClusterCredentials(username=username, password=password)
    except ApiException:
        pass
    return None


def _process_datacenter(dc: dict, cluster_name: str, cluster_namespace: str,
                       namespace: Optional[str], service_suffix: str, core_api,
                       credentials: Optional[ClusterCredentials], discovered_clusters: dict):
    dc_name = dc.get("metadata", {}).get("name")
    if not dc_name:
        return

    service_names = _build_service_names(cluster_name, dc_name, service_suffix)
    
    for svc_name in service_names:
        contact_points = _discover_service_contact_points(core_api, svc_name, cluster_namespace)
        if contact_points:
            config_key = _build_config_key(cluster_name, cluster_namespace, namespace)
            discovered_clusters[config_key] = ClusterConnectionConfig(
                contact_points=contact_points,
                port=9042,
                credentials=credentials
            )
            logger.info(f"Discovered cluster {config_key} from service {svc_name}")
            break


def _build_service_names(cluster_name: str, dc_name: str, service_suffix: str) -> list[str]:
    service_names = []
    if service_suffix:
        service_names.append(f"{cluster_name}-{dc_name}{service_suffix}")
    service_names.append(f"{cluster_name}-{dc_name}-service")
    return service_names


def _discover_service_contact_points(core_api, svc_name: str, 
                                     cluster_namespace: str) -> Optional[list[str]]:
    try:
        svc = core_api.read_namespaced_service(svc_name, cluster_namespace)
        contact_points = []
        svc_spec = svc.spec
        svc_status = svc.status

        if svc_spec.type == "LoadBalancer":
            ingresses = svc_status.load_balancer.ingress or []
            for ing in ingresses:
                if ing.ip:
                    contact_points.append(ing.ip)
                if ing.hostname:
                    contact_points.append(ing.hostname)

        if svc_spec.external_i_ps:
            contact_points.extend(svc_spec.external_i_ps)

        if not contact_points and svc_spec.cluster_ip and svc_spec.cluster_ip != "None":
            contact_points.append(svc_spec.cluster_ip)

        if not contact_points:
            svc_dns = f"{svc_name}.{cluster_namespace}.svc.cluster.local"
            contact_points.append(svc_dns)

        return contact_points if contact_points else None
    except ApiException:
        return None


def _build_config_key(cluster_name: str, cluster_namespace: str, 
                      namespace: Optional[str]) -> str:
    if namespace and namespace != cluster_namespace:
        return f"{cluster_namespace}-{cluster_name}"
    return cluster_name
