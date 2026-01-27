from typing import Optional
from logging import getLogger
from kubernetes.client import CoreV1Api, CustomObjectsApi, ApiException

logger = getLogger(__name__)


def get_recovery_status(core_api: CoreV1Api, custom_api: CustomObjectsApi, enabled: bool) -> dict:
    if not enabled:
        return {"jobs": [], "total": 0}

    recoveries = {}
    
    _collect_pending_recoveries(core_api, recoveries)
    
    _collect_active_recoveries(custom_api, recoveries)

    return _build_status_summary(list(recoveries.values()))


def approve_recovery(core_api: CoreV1Api, custom_api: CustomObjectsApi, recovery_id: str, approved_by: str):
    pod_name = _parse_recovery_id(recovery_id)
    
    pod = _get_pod_or_raise(core_api, pod_name)
    cluster_name = _get_cluster_name_or_raise(pod)
    
    _create_replacenode_task(
        custom_api=custom_api, 
        namespace=pod.metadata.namespace, 
        pod_name=pod_name, 
        node_name=pod.spec.node_name or "unknown", 
        cluster_name=cluster_name,
        approved_by=approved_by
    )


def cancel_recovery(custom_api: CustomObjectsApi, recovery_id: str):
    pod_name = _parse_recovery_id(recovery_id)
    task = _find_task_by_pod_name(custom_api, pod_name)
    
    if not task:
        raise ValueError("No active recovery task found to cancel")
    
    _delete_task(custom_api, task)



def _collect_pending_recoveries(core_api: CoreV1Api, recoveries: dict[str, dict]):
    try:
        pending_pods = _fetch_pending_k8ssandra_pods(core_api)
        
        for pod in pending_pods:
            if not _has_volume_affinity_issue(pod):
                continue

            rec_id = _get_recovery_id(pod.metadata.name)
            recoveries[rec_id] = _build_pending_recovery_entry(rec_id, pod)
            
    except Exception as e:
        logger.error(f"Error listing pending pods: {e}")


def _collect_active_recoveries(custom_api: CustomObjectsApi, recoveries: dict[str, dict]):
    try:
        tasks = _fetch_all_k8ssandra_tasks(custom_api)
        
        for task in tasks:
            pod_name = _extract_pod_name_from_task(task)
            if not pod_name:
                continue

            rec_id = _get_recovery_id(pod_name)
            recoveries[rec_id] = _build_active_recovery_entry(rec_id, pod_name, task)
            
    except Exception as e:
        logger.error(f"Error listing K8ssandraTasks: {e}")


def _build_status_summary(job_list: list[dict]) -> dict:
    return {
        "total": len(job_list),
        "pending_approval": len([r for r in job_list if r["state"] == "pending-approval"]),
        "active": len([r for r in job_list if r["state"] == "active"]),
        "completed": len([r for r in job_list if r["state"] == "completed"]),
        "failed": len([r for r in job_list if r["state"] == "failed"]),
        "jobs": job_list
    }



def _fetch_pending_k8ssandra_pods(core_api: CoreV1Api) -> list:
    resp = core_api.list_pod_for_all_namespaces(
        field_selector="status.phase=Pending",
        label_selector="app.kubernetes.io/managed-by=k8ssandra-operator"
    )
    return resp.items


def _fetch_all_k8ssandra_tasks(custom_api: CustomObjectsApi) -> list[dict]:
    try:
        resp = custom_api.list_cluster_custom_object(
            group="control.k8ssandra.io",
            version="v1alpha1",
            plural="k8ssandratasks"
        )
        return resp.get("items", [])
    except ApiException:
        return []


def _create_replacenode_task(
    custom_api: CustomObjectsApi, 
    namespace: str, 
    pod_name: str, 
    node_name: str, 
    cluster_name: str, 
    approved_by: str
):
    existing_task = _find_task_by_pod_name(custom_api, pod_name)
    
    if existing_task:
        status = existing_task.get("status", {})
        is_running = status.get("active", 0) > 0
        is_completed = status.get("succeeded", 0) > 0
        is_failed = status.get("failed", 0) > 0
        
        if is_running:
            logger.info(f"Task already running for pod {pod_name}, skipping duplicate creation")
            return
        
        if is_completed or is_failed:
            logger.warning(
                f"Pod {pod_name} failed again after previous recovery attempt. "
                f"Previous task: {existing_task['metadata']['name']}, "
                f"Previous result: {'succeeded' if is_completed else 'failed'}. "
                f"Deleting old task and creating new recovery attempt."
            )
            _delete_task(custom_api, existing_task)
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            task_name = f"replacenode-{pod_name}-{timestamp}".replace(":", "-").lower()
        else:
            logger.info(f"Task exists but status unknown for {pod_name}, skipping")
            return
    else:
        task_name = f"replacenode-{pod_name}".replace(":", "-").lower()
    
    task_body = {
        "apiVersion": "control.k8ssandra.io/v1alpha1",
        "kind": "K8ssandraTask",
        "metadata": {
            "name": task_name,
            "namespace": namespace,
            "labels": {
                "cassanova.io/recovery-pod": pod_name,
                "cassanova.io/recovery-node": node_name.replace(":", "-").lower()
            },
            "annotations": {
                "cassanova.io/approved-by": approved_by,
                "cassanova.io/approval-time": datetime.utcnow().isoformat()
            }
        },
        "spec": {
            "cluster": {"name": cluster_name},
            "ttlSecondsAfterFinished": 86400,
            "template": {
                "jobs": [{
                    "command": "replacenode",
                    "args": {"pod_name": pod_name}
                }]
            }
        }
    }
    
    try:
        custom_api.create_namespaced_custom_object(
            group="control.k8ssandra.io",
            version="v1alpha1",
            namespace=namespace,
            plural="k8ssandratasks",
            body=task_body
        )
        logger.info(f"Created K8ssandraTask {task_name} for pod {pod_name} (approver: {approved_by})")
    except ApiException as e:
        if e.status == 409:
            logger.info(f"Task {task_name} already exists")
            logger.info(f"Task {task_name} already exists (race condition), treating as success")
        else:
            raise


def _delete_task(custom_api: CustomObjectsApi, task: dict):
    name = task["metadata"]["name"]
    namespace = task["metadata"]["namespace"]
    try:
        custom_api.delete_namespaced_custom_object(
            group="control.k8ssandra.io",
            version="v1alpha1",
            namespace=namespace,
            plural="k8ssandratasks",
            name=name
        )
        logger.info(f"Deleted task {name}")
    except ApiException as e:
        logger.error(f"Failed to delete task: {e}")



def _get_recovery_id(pod_name: str) -> str:
    return f"rec-{pod_name}"


def _parse_recovery_id(recovery_id: str) -> str:
    if not recovery_id.startswith("rec-"):
        raise ValueError("Invalid recovery ID format")
    return recovery_id[4:]


def _build_pending_recovery_entry(rec_id: str, pod) -> dict:
    return {
        "id": rec_id,
        "node_name": pod.spec.node_name or "unknown-node",
        "state": "pending-approval",
        "cluster_name": pod.metadata.labels.get("k8ssandra.io/cluster-name", "unknown"),
        "datacenter": pod.metadata.labels.get("cassandra.datastax.com/datacenter", "unknown"),
        "rack": pod.metadata.labels.get("cassandra.datastax.com/rack", "unknown"),
        "pod_name": pod.metadata.name,
        "namespace": pod.metadata.namespace,
        "detected_at": _safe_isoformat(pod.metadata.creation_timestamp),
        "k8ssandra_task_name": None,
        "error": None
    }


def _build_active_recovery_entry(rec_id: str, pod_name: str, task: dict) -> dict:
    state = "active"
    status = task.get("status", {})
    if status.get("succeeded", 0) > 0:
        state = "completed"
    elif status.get("failed", 0) > 0:
        state = "failed"
        
    return {
        "id": rec_id,
        "node_name": "unknown",
        "state": state,
        "cluster_name": task.get("spec", {}).get("cluster", {}).get("name", "unknown"),
        "datacenter": "unknown",
        "rack": "unknown",
        "pod_name": pod_name,
        "namespace": task["metadata"]["namespace"],
        "detected_at": task["metadata"]["creationTimestamp"],
        "k8ssandra_task_name": task["metadata"]["name"],
        "error": "Task failed" if state == "failed" else None
    }


def _extract_pod_name_from_task(task: dict) -> Optional[str]:
    try:
        jobs = task.get("spec", {}).get("template", {}).get("jobs", [])
        if not jobs:
            return None
        return jobs[0].get("args", {}).get("pod_name")
    except (AttributeError, KeyError):
        return None


def _find_task_by_pod_name(custom_api: CustomObjectsApi, pod_name: str) -> Optional[dict]:
    tasks = _fetch_all_k8ssandra_tasks(custom_api)
    for task in tasks:
        if _extract_pod_name_from_task(task) == pod_name:
            return task
    return None


def _get_pod_or_raise(core_api: CoreV1Api, name: str):
    try:
        resp = core_api.list_pod_for_all_namespaces(
            field_selector=f"metadata.name={name}"
        )
        if resp.items:
            return resp.items[0]
    except ApiException:
        pass
    return None


def _get_cluster_name_or_raise(pod) -> str:
    cluster_name = pod.metadata.labels.get("k8ssandra.io/cluster-name")
    if not cluster_name:
        raise ValueError("Pod missing cluster-name label")
    return cluster_name


def _has_volume_affinity_issue(pod) -> bool:
    if not pod.status.conditions:
        return False
        
    for condition in pod.status.conditions:
        if condition.type == "PodScheduled" and condition.status == "False":
            msg = (condition.message or "").lower()
            if "volume node affinity" in msg:
                return True
            if "volume" in msg and "affinity" in msg:
                return True
    return False


def _safe_isoformat(dt) -> Optional[str]:
    return dt.isoformat() if dt else None
