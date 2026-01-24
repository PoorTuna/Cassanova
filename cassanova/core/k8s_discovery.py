import base64
import os
from typing import Optional, Dict
from logging import getLogger

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
) -> Dict[str, ClusterConnectionConfig]:
    print(f"[K8s Discovery] Starting discovery with kubeconfig={kubeconfig_path}, namespace={namespace}, suffix={service_suffix}")
    
    if not K8S_AVAILABLE:
        print("[K8s Discovery] Kubernetes package not installed. Skipping.")
        logger.warning("Kubernetes package not installed. Skipping K8s discovery.")
        return {}

    try:
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            print(f"[K8s Discovery] Loading kubeconfig from {kubeconfig_path}")
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            print(f"[K8s Discovery] Kubeconfig path not found or not provided, trying fallback...")
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config()
    except Exception as e:
        print(f"[K8s Discovery] Failed to load kubeconfig: {e}")
        logger.error(f"Failed to load kubeconfig: {e}")
        return {}

    discovered_clusters = {}
    custom_api = client.CustomObjectsApi()
    core_api = client.CoreV1Api()

    try:
        if namespace:
            k8s_clusters = custom_api.list_namespaced_custom_object(
                group="k8ssandra.io",
                version="v1alpha1",
                namespace=namespace,
                plural="k8ssandraclusters"
            )
        else:
            k8s_clusters = custom_api.list_cluster_custom_object(
                group="k8ssandra.io",
                version="v1alpha1",
                plural="k8ssandraclusters"
            )
    except ApiException as e:
        if e.status == 404:
            print("[K8s Discovery] No K8ssandraCluster CRDs found (404).")
            logger.info("No K8ssandraCluster CRDs found.")
        else:
            print(f"[K8s Discovery] Error listing K8ssandraClusters: {e}")
            logger.error(f"Error listing K8ssandraClusters: {e}")
        return {}

    items = k8s_clusters.get("items", [])
    print(f"[K8s Discovery] Found {len(items)} K8ssandraClusters.")
    logger.info(f"Found {len(items)} K8ssandraClusters.")

    for item in items:
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        cluster_name = metadata.get("name")
        cluster_namespace = metadata.get("namespace", "default")
        
        if not cluster_name:
            continue

        secret_name = f"{cluster_name}-superuser"
        
        credentials = None
        try:
            secret = core_api.read_namespaced_secret(secret_name, cluster_namespace)
            data = secret.data or {}
            username_b64 = data.get("username")
            password_b64 = data.get("password")
            
            if username_b64 and password_b64:
                username = base64.b64decode(username_b64).decode('utf-8')
                password = base64.b64decode(password_b64).decode('utf-8')
                credentials = ClusterCredentials(username=username, password=password)
        except ApiException:
            pass

        datacenters = spec.get("cassandra", {}).get("datacenters", [])
        
        for dc in datacenters:
            dc_name = dc.get("metadata", {}).get("name")
            if not dc_name:
                continue
                
            service_names = []
            if service_suffix:
                service_names.append(f"{cluster_name}-{dc_name}{service_suffix}")
            
            service_names.append(f"{cluster_name}-{dc_name}-service")

            found_service = False
            for svc_name in service_names:
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
                                
                    if svc_spec.external_ips:
                        contact_points.extend(svc_spec.external_ips)
                        
                    if not contact_points and svc_spec.cluster_ip and svc_spec.cluster_ip != "None":
                         contact_points.append(svc_spec.cluster_ip)

                    if contact_points:
                        config_key = f"{cluster_name}"
                        if namespace and namespace != cluster_namespace:
                           config_key = f"{cluster_namespace}-{cluster_name}"

                        discovered_clusters[config_key] = ClusterConnectionConfig(
                            contact_points=contact_points,
                            port=9042,
                            credentials=credentials
                        )
                        logger.info(f"Discovered cluster {config_key} from service {svc_name}")
                        found_service = True
                        break

                except ApiException:
                    continue
            
            if found_service:
                break

    return discovered_clusters
