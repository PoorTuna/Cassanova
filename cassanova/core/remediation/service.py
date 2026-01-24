import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from logging import getLogger

from kubernetes import client
from kubernetes.client import ApiException

logger = getLogger(__name__)


class RemediationService:
    """
    Simple polling-based remediation service.
    State stored in K8s ConfigMap.
    Runs synchronously in a background thread.
    """
    
    def __init__(self, core_api: client.CoreV1Api, custom_api: client.CustomObjectsApi, config):
        self.core_api = core_api
        self.custom_api = custom_api
        self.config = config
        self.running = False
        self._thread = None
    
    def start(self):
        """Start background remediation loop in a thread"""
        if not self.config.enabled:
            logger.info("Remediation service disabled")
            return
        
        logger.info("Starting remediation service...")
        self.running = True
        self._thread = threading.Thread(target=self._remediation_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop remediation loop"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def scan_now(self):
        """Trigger immediate scan"""
        try:
            state = self._load_state()
            self._detect_new_failures(state)
            self._save_state(state)
            return {"status": "scan_complete"}
        except Exception as e:
            logger.error(f"Manual scan error: {e}", exc_info=True)
            raise


    
    def _remediation_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                state = self._load_state()
                
                # Only auto-detect if enabled
                if self.config.auto_poll_enabled:
                    self._detect_new_failures(state)
                
                self._process_remediations(state)
                self._save_state(state)
            except Exception as e:
                logger.error(f"Remediation loop error: {e}", exc_info=True)
            
            time.sleep(self.config.poll_interval_seconds)
    
    def _load_state(self) -> dict:
        """Load state from ConfigMap"""
        try:
            cm = self.core_api.read_namespaced_config_map(
                name="cassanova-remediation-state",
                namespace="default"
            )
            return json.loads(cm.data["state.json"])
        except ApiException as e:
            if e.status == 404:
                empty_state = {"remediations": {}, "governor": {}}
                self._save_state(empty_state)
                return empty_state
            raise
    
    def _save_state(self, state: dict):
        """Save state to ConfigMap"""
        cm_body = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(
                name="cassanova-remediation-state",
                namespace="default"
            ),
            data={
                "state.json": json.dumps(state, indent=2)
            }
        )
        
        try:
            self.core_api.replace_namespaced_config_map(
                name="cassanova-remediation-state",
                namespace="default",
                body=cm_body
            )
        except ApiException as e:
            if e.status == 404:
                self.core_api.create_namespaced_config_map(
                    namespace="default",
                    body=cm_body
                )
    
    def _detect_new_failures(self, state: dict):
        """Detect pending pods with volume affinity issues"""
        # Find all pending pods managed by k8ssandra
        pods_response = self.core_api.list_pod_for_all_namespaces(
            field_selector="status.phase=Pending",
            label_selector="app.kubernetes.io/managed-by=k8ssandra-operator"
        )
        
        for pod in pods_response.items:
            # Check if this pod is already in remediation state
            if any(r["pod_name"] == pod.metadata.name for r in state["remediations"].values()):
                continue
            
            # Verify it has volume affinity issues
            if not self._has_volume_affinity_issue(pod):
                continue
            
            # Found a candidate!
            node_name = pod.spec.node_name or "unknown-node"
            remediation_id = f"rem-{pod.metadata.name}-{int(time.time())}"
            
            state["remediations"][remediation_id] = {
                "id": remediation_id,
                "node_name": node_name,  # Might be None/empty if pending
                "node_ip": "unknown",
                "state": "pending-approval",
                "cluster_name": pod.metadata.labels.get("k8ssandra.io/cluster-name", "unknown"),
                "datacenter": pod.metadata.labels.get("cassandra.datastax.com/datacenter", "unknown"),
                "rack": pod.metadata.labels.get("cassandra.datastax.com/rack", "unknown"),
                "pod_name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "pvcs": self._get_pod_pvcs(pod),
                "k8ssandra_task_name": None,
                "detected_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "approved_at": None,
                "approved_by": None,
                "error": None
            }
            
            logger.info(f"Detected pending pod {pod.metadata.name} (Volume Affinity) - PENDING APPROVAL")

    def _has_volume_affinity_issue(self, pod) -> bool:
        """Check events or conditions for volume affinity constraints"""
        # Check Pod Conditions first
        if pod.status.conditions:
            for condition in pod.status.conditions:
                if condition.type == "PodScheduled" and condition.status == "False":
                    if "volume node affinity" in (condition.message or "").lower():
                        return True
                    if "volume" in (condition.message or "").lower() and "affinity" in (condition.message or "").lower():
                        return True
        
        # NOTE: Ideally we would also check Events, but listing events for every pod is expensive.
        # usually PodScheduled condition status=False reason=Unschedulable message has the info.
        return False
    
    def _process_remediations(self, state: dict):
        """Process approved remediations"""
        for rem_id, remediation in list(state["remediations"].items()):
            current_state = remediation["state"]
            
            try:
                if current_state == "pending-approval":
                    pass
                elif current_state == "approved":
                    self._handle_approved(remediation, state)
                elif current_state == "finalizers-removed":
                    self._handle_finalizers_removed(remediation, state)
                elif current_state == "k8ssandra-task-scheduled":
                    self._handle_task_scheduled(remediation, state)
                elif current_state == "completed":
                    self._handle_completed(remediation, state)
                
                remediation["updated_at"] = datetime.utcnow().isoformat()
                
            except Exception as e:
                logger.error(f"Error processing {rem_id}: {e}", exc_info=True)
                remediation["state"] = "failed"
                remediation["error"] = str(e)
    
    def _handle_approved(self, remediation: dict, state: dict):
        """Skip taint, go straight to removing finalizers"""
        if not self._can_start_remediation(remediation, state):
            return
            
        self._register_governor(remediation, state)
        
        # Skip taint, proceed to remove finalizers
        self._handle_finalizers_removed_logic(remediation)
        
        remediation["state"] = "finalizers-removed"
        logger.info(f"Approved -> Finalizers removed for {remediation['pod_name']}")
    
    def _handle_finalizers_removed_logic(self, remediation: dict):
        """Logic to remove finalizers from PVCs and Pod"""
        pod_name = remediation["pod_name"]
        namespace = remediation["namespace"]
        
        for pvc_name in remediation["pvcs"]:
            try:
                self.core_api.patch_namespaced_persistent_volume_claim(
                    pvc_name,
                    namespace,
                    {"metadata": {"finalizers": None}}
                )
            except ApiException:
                pass
        
        try:
            self.core_api.patch_namespaced_pod(
                pod_name,
                namespace,
                {"metadata": {"finalizers": None}}
            )
        except ApiException:
            pass
    
    def _handle_finalizers_removed(self, remediation: dict, state: dict):
        """Create K8ssandraTask"""
        task_name = f"replacenode-{remediation['node_name']}-{remediation['pod_name']}"
        # Sanitize task name (k8s names must be lowercase alphanumeric)
        task_name = task_name.replace(":", "-").lower()
        
        try:
            self.custom_api.get_namespaced_custom_object(
                group="control.k8ssandra.io",
                version="v1alpha1",
                namespace=remediation["namespace"],
                plural="k8ssandratasks",
                name=task_name
            )
            remediation["k8ssandra_task_name"] = task_name
            remediation["state"] = "k8ssandra-task-scheduled"
            return
        except ApiException:
            pass
        
        # Find which node it was *supposed* to be on (wait, if pending due to volume affinity,
        # it was likely trying to schedule on a specific node). 
        # But replacenode just requires the POD name. The operator handles the rest.
        
        task = {
            "apiVersion": "control.k8ssandra.io/v1alpha1",
            "kind": "K8ssandraTask",
            "metadata": {
                "name": task_name,
                "namespace": remediation["namespace"]
            },
            "spec": {
                "cluster": {"name": remediation["cluster_name"]},
                "template": {
                    "jobs": [{
                        "command": "replacenode",
                        "args": {"pod_name": remediation["pod_name"]}
                    }]
                }
            }
        }
        
        self.custom_api.create_namespaced_custom_object(
            group="control.k8ssandra.io",
            version="v1alpha1",
            namespace=remediation["namespace"],
            plural="k8ssandratasks",
            body=task
        )
        
        remediation["k8ssandra_task_name"] = task_name
        remediation["state"] = "k8ssandra-task-scheduled"
        logger.info(f"Created K8ssandraTask: {task_name}")
    
    def _handle_task_scheduled(self, remediation: dict, state: dict):
        """Monitor K8ssandraTask completion"""
        task_name = remediation["k8ssandra_task_name"]
        
        task = self.custom_api.get_namespaced_custom_object(
            group="control.k8ssandra.io",
            version="v1alpha1",
            namespace=remediation["namespace"],
            plural="k8ssandratasks",
            name=task_name
        )
        
        status = task.get("status", {})
        
        if status.get("succeeded", 0) > 0:
            remediation["state"] = "completed"
            self._unregister_governor(remediation, state)
            logger.info(f"Remediation completed: {remediation['id']}")
        elif status.get("failed", 0) > 0:
            remediation["state"] = "failed"
            remediation["error"] = "K8ssandraTask failed"
            self._unregister_governor(remediation, state)
    
    def _handle_completed(self, remediation: dict, state: dict):
        """Cleanup completed remediations after 24h"""
        completed_at = datetime.fromisoformat(remediation["updated_at"])
        
        if datetime.utcnow() - completed_at > timedelta(hours=24):
            del state["remediations"][remediation["id"]]
            logger.info(f"Cleaned up remediation: {remediation['id']}")
    
    def _is_node_failed(self, node) -> bool:
        """Check if node is NotReady"""
        if not node.status.conditions:
            return False
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status != "True":
                return True
        return False
    
    def _get_node_ip(self, node) -> str:
        """Extract node IP"""
        if not node.status.addresses:
            return "unknown"
        for addr in node.status.addresses:
            if addr.type == "InternalIP":
                return addr.address
        return "unknown"
    
    def _get_pod_pvcs(self, pod) -> list:
        """Get PVC names for pod"""
        pvcs = []
        if not pod.spec.volumes:
            return pvcs
        for volume in pod.spec.volumes:
            if volume.persistent_volume_claim:
                pvcs.append(volume.persistent_volume_claim.claim_name)
        return pvcs
    
    def _can_start_remediation(self, remediation: dict, state: dict) -> bool:
        """Check governor limits"""
        dc = remediation["datacenter"]
        rack = remediation["rack"]
        
        dc_active = state["governor"].get(dc, {}).get("active", 0)
        rack_active = state["governor"].get(rack, {}).get("active", 0)
        
        if dc_active >= self.config.max_concurrent_per_dc:
            return False
        if rack_active >= self.config.max_concurrent_per_rack:
            return False
        
        return True
    
    def _register_governor(self, remediation: dict, state: dict):
        """Register active remediation"""
        dc = remediation["datacenter"]
        rack = remediation["rack"]
        
        if dc not in state["governor"]:
            state["governor"][dc] = {"active": 0, "jobs": []}
        if rack not in state["governor"]:
            state["governor"][rack] = {"active": 0, "jobs": []}
        
        state["governor"][dc]["active"] += 1
        state["governor"][dc]["jobs"].append(remediation["id"])
        
        state["governor"][rack]["active"] += 1
        state["governor"][rack]["jobs"].append(remediation["id"])
    
    def _unregister_governor(self, remediation: dict, state: dict):
        """Unregister completed remediation"""
        dc = remediation["datacenter"]
        rack = remediation["rack"]
        
        if dc in state["governor"]:
            state["governor"][dc]["active"] = max(0, state["governor"][dc]["active"] - 1)
            if remediation["id"] in state["governor"][dc]["jobs"]:
                state["governor"][dc]["jobs"].remove(remediation["id"])
        
        if rack in state["governor"]:
            state["governor"][rack]["active"] = max(0, state["governor"][rack]["active"] - 1)
            if remediation["id"] in state["governor"][rack]["jobs"]:
                state["governor"][rack]["jobs"].remove(remediation["id"])
    
    def approve_remediation(self, remediation_id: str, approved_by: str):
        """Approve a remediation (called from API)"""
        state = self._load_state()
        
        if remediation_id not in state["remediations"]:
            raise ValueError(f"Remediation {remediation_id} not found")
        
        remediation = state["remediations"][remediation_id]
        
        if remediation["state"] != "pending-approval":
            raise ValueError(f"Remediation {remediation_id} is not pending approval (state: {remediation['state']})")
        
        remediation["state"] = "approved"
        remediation["approved_at"] = datetime.utcnow().isoformat()
        remediation["approved_by"] = approved_by
        
        self._save_state(state)
        
        logger.info(f"Remediation {remediation_id} approved by {approved_by}")
    
    def cancel_remediation(self, remediation_id: str):
        """Cancel a remediation"""
        state = self._load_state()
        
        if remediation_id not in state["remediations"]:
            raise ValueError(f"Remediation {remediation_id} not found")
        
        remediation = state["remediations"][remediation_id]
        
        if remediation["state"] in ["completed", "failed"]:
            raise ValueError(f"Cannot cancel remediation in state: {remediation['state']}")
        
        if remediation["state"] not in ["pending-approval", "approved"]:
            self._unregister_governor(remediation, state)
        
        remediation["state"] = "cancelled"
        
        self._save_state(state)
        
        logger.info(f"Remediation {remediation_id} cancelled")
    
    def get_status(self) -> dict:
        """Get current remediation status"""
        state = self._load_state()
        
        return {
            "total": len(state["remediations"]),
            "pending_approval": len([r for r in state["remediations"].values() if r["state"] == "pending-approval"]),
            "active": len([r for r in state["remediations"].values() if r["state"] not in ["pending-approval", "completed", "failed", "cancelled"]]),
            "completed": len([r for r in state["remediations"].values() if r["state"] == "completed"]),
            "failed": len([r for r in state["remediations"].values() if r["state"] == "failed"]),
            "jobs": list(state["remediations"].values())
        }
