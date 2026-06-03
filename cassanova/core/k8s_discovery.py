import base64
import fnmatch
import os
from dataclasses import dataclass
from logging import getLogger
from typing import Any

try:
    from kubernetes import client, config
    from kubernetes.client import ApiException

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

from cassanova.config.cluster_config import ClusterConnectionConfig, ClusterCredentials

logger = getLogger(__name__)


class KubernetesDiscoveryError(Exception):
    pass


def _cluster_name_allowed(name: str, include: list[str], exclude: list[str]) -> bool:
    if any(fnmatch.fnmatchcase(name, p) for p in exclude):
        return False
    if not include:
        return True
    return any(fnmatch.fnmatchcase(name, p) for p in include)


@dataclass
class DiscoveredCluster:
    config: ClusterConnectionConfig
    context: str | None


def discover_k8s_clusters(
    kubeconfig_path: str | None = None,
    namespace: str | None = None,
    service_suffix: str = "-service",
    contexts: list[str] | None = None,
    external_only: bool = False,
    cluster_include: list[str] | None = None,
    cluster_exclude: list[str] | None = None,
) -> dict[str, DiscoveredCluster]:
    if not K8S_AVAILABLE:
        logger.warning("Kubernetes package not installed. Skipping K8s discovery.")
        return {}

    include = cluster_include or []
    exclude = cluster_exclude or []
    target_contexts = _resolve_contexts(kubeconfig_path, contexts)

    if target_contexts is None:
        return _discover_for_context(
            kubeconfig_path, None, namespace, service_suffix, external_only, include, exclude, prefix=False
        )

    discovered: dict[str, DiscoveredCluster] = {}
    successful_queries = 0
    multi = len(target_contexts) > 1

    for ctx in target_contexts:
        try:
            ctx_discovered = _discover_for_context(
                kubeconfig_path, ctx, namespace, service_suffix, external_only, include, exclude, prefix=multi
            )
            successful_queries += 1
            for key, value in ctx_discovered.items():
                if key in discovered:
                    logger.warning(f"Duplicate cluster key '{key}' across contexts; overwriting.")
                discovered[key] = value
        except KubernetesDiscoveryError as e:
            logger.error(f"Failed to query context '{ctx}': {e}")

    if successful_queries == 0 and target_contexts:
        raise KubernetesDiscoveryError("No kubeconfig contexts could be reached")

    return discovered


def _resolve_contexts(
    kubeconfig_path: str | None, contexts: list[str] | None
) -> list[str] | None:
    if contexts:
        return contexts

    if not kubeconfig_path or not os.path.exists(kubeconfig_path):
        return None

    try:
        all_contexts, _ = config.list_kube_config_contexts(config_file=kubeconfig_path)
    except Exception as e:
        logger.error(f"Failed to list kubeconfig contexts: {e}")
        return None

    return [c["name"] for c in all_contexts if c.get("name")]


def _discover_for_context(
    kubeconfig_path: str | None,
    context: str | None,
    namespace: str | None,
    service_suffix: str,
    external_only: bool,
    cluster_include: list[str],
    cluster_exclude: list[str],
    prefix: bool,
) -> dict[str, DiscoveredCluster]:
    _load_k8s_config(kubeconfig_path, context)

    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()

    k8s_clusters = _fetch_k8ssandra_clusters(custom_api, namespace)
    items = k8s_clusters.get("items", [])
    logger.info(f"Context '{context or 'default'}': found {len(items)} K8ssandraClusters.")

    raw: dict[str, ClusterConnectionConfig] = {}
    for item in items:
        _process_k8ssandra_cluster(
            item, core_api, namespace, service_suffix, external_only, cluster_include, cluster_exclude, raw
        )

    result: dict[str, DiscoveredCluster] = {}
    for key, cc in raw.items():
        prefixed_key = f"{context}/{key}" if prefix and context else key
        result[prefixed_key] = DiscoveredCluster(config=cc, context=context)
    return result


def _load_k8s_config(kubeconfig_path: str | None, context: str | None = None) -> None:
    try:
        if kubeconfig_path and os.path.exists(kubeconfig_path):
            config.load_kube_config(config_file=kubeconfig_path, context=context)
        else:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                config.load_kube_config(context=context)
    except Exception as e:
        raise KubernetesDiscoveryError(
            f"Failed to load kubeconfig (context={context}): {e}"
        ) from e


def _fetch_k8ssandra_clusters(custom_api: Any, namespace: str | None) -> dict[str, Any]:
    try:
        if namespace:
            return custom_api.list_namespaced_custom_object(  # type: ignore[no-any-return]
                group="k8ssandra.io",
                version="v1alpha1",
                namespace=namespace,
                plural="k8ssandraclusters",
            )
        else:
            return custom_api.list_cluster_custom_object(  # type: ignore[no-any-return]
                group="k8ssandra.io", version="v1alpha1", plural="k8ssandraclusters"
            )
    except ApiException as e:
        if e.status == 404:
            logger.info("No K8ssandraCluster CRDs found.")
            return {"items": []}
        raise KubernetesDiscoveryError(
            f"K8s API error listing K8ssandraClusters (status={e.status}): {e}"
        ) from e


def _process_k8ssandra_cluster(
    item: dict[str, Any],
    core_api: Any,
    namespace: str | None,
    service_suffix: str,
    external_only: bool,
    cluster_include: list[str],
    cluster_exclude: list[str],
    discovered_clusters: dict[str, ClusterConnectionConfig],
) -> None:
    metadata = item.get("metadata", {})
    spec = item.get("spec", {})
    cluster_name = metadata.get("name")
    cluster_namespace = metadata.get("namespace", "default")

    if not cluster_name:
        return

    if not _cluster_name_allowed(cluster_name, cluster_include, cluster_exclude):
        logger.debug(f"Skipping cluster '{cluster_name}' (filtered by include/exclude)")
        return

    credentials = _extract_cluster_credentials(core_api, cluster_name, cluster_namespace)
    datacenters = spec.get("cassandra", {}).get("datacenters", [])

    for dc in datacenters:
        _process_datacenter(
            dc,
            cluster_name,
            cluster_namespace,
            namespace,
            service_suffix,
            external_only,
            core_api,
            credentials,
            discovered_clusters,
        )


def _extract_cluster_credentials(
    core_api: Any, cluster_name: str, cluster_namespace: str
) -> ClusterCredentials | None:
    secret_name = f"{cluster_name}-superuser"
    try:
        secret = core_api.read_namespaced_secret(secret_name, cluster_namespace)
        data = secret.data or {}
        username_b64 = data.get("username")
        password_b64 = data.get("password")

        if username_b64 and password_b64:
            username = base64.b64decode(username_b64).decode("utf-8")
            password = base64.b64decode(password_b64).decode("utf-8")
            return ClusterCredentials(username=username, password=password)
    except ApiException:
        pass
    return None


def _process_datacenter(
    dc: dict[str, Any],
    cluster_name: str,
    cluster_namespace: str,
    namespace: str | None,
    service_suffix: str,
    external_only: bool,
    core_api: Any,
    credentials: ClusterCredentials | None,
    discovered_clusters: dict[str, ClusterConnectionConfig],
) -> None:
    dc_name = dc.get("metadata", {}).get("name")
    if not dc_name:
        return

    service_names = _build_service_names(cluster_name, dc_name, service_suffix)

    for svc_name in service_names:
        contact_points = _discover_service_contact_points(
            core_api, svc_name, cluster_namespace, external_only
        )
        if contact_points:
            config_key = _build_config_key(cluster_name, cluster_namespace, namespace)
            discovered_clusters[config_key] = ClusterConnectionConfig(
                contact_points=contact_points, port=9042, credentials=credentials
            )
            logger.info(f"Discovered cluster {config_key} from service {svc_name}")
            break


def _build_service_names(cluster_name: str, dc_name: str, service_suffix: str) -> list[str]:
    service_names = []
    if service_suffix:
        service_names.append(f"{cluster_name}-{dc_name}{service_suffix}")
    service_names.append(f"{cluster_name}-{dc_name}-service")
    return service_names


def _discover_service_contact_points(
    core_api: Any,
    svc_name: str,
    cluster_namespace: str,
    external_only: bool = False,
) -> list[str] | None:
    try:
        svc = core_api.read_namespaced_service(svc_name, cluster_namespace)
    except ApiException:
        return None

    contact_points: list[str] = []
    svc_spec = svc.spec
    svc_status = svc.status

    if svc_spec.type == "LoadBalancer":
        for ing in svc_status.load_balancer.ingress or []:
            if ing.ip:
                contact_points.append(ing.ip)
            if ing.hostname:
                contact_points.append(ing.hostname)

    if svc_spec.external_ips:
        contact_points.extend(svc_spec.external_ips)

    if external_only:
        return contact_points or None

    if not contact_points and svc_spec.cluster_ip and svc_spec.cluster_ip != "None":
        contact_points.append(svc_spec.cluster_ip)

    if not contact_points:
        contact_points.append(f"{svc_name}.{cluster_namespace}.svc.cluster.local")

    return contact_points or None


def _build_config_key(cluster_name: str, cluster_namespace: str, namespace: str | None) -> str:
    if namespace and namespace != cluster_namespace:
        return f"{cluster_namespace}-{cluster_name}"
    return cluster_name
