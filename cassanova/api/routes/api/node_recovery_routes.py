from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from cassanova.config.cassanova_config import get_clusters_config
from cassanova.core.node_recovery import pod_recovery

node_recovery_router = APIRouter(prefix='/node-recovery', tags=['Node Recovery'])


def get_k8s_context(request: Request):
    core = getattr(request.app.state, "k8s_core", None)
    custom = getattr(request.app.state, "k8s_custom", None)
    config = get_clusters_config()

    if not core or not custom:
        return None

    return {
        "core": core,
        "custom": custom,
        "enabled": config.k8s.node_recovery.enabled
    }


class ApproveRequest(BaseModel):
    recovery_id: str
    approved_by: str


@node_recovery_router.get("/status")
def get_status_route(ctx=Depends(get_k8s_context)):
    if not ctx:
        raise HTTPException(503, "Kubernetes connection not available")

    return pod_recovery.get_recovery_status(ctx["core"], ctx["custom"], ctx["enabled"])


@node_recovery_router.post("/approve")
def approve_route(body: ApproveRequest, ctx=Depends(get_k8s_context)):
    if not ctx:
        raise HTTPException(503, "Kubernetes connection not available")

    if not ctx["enabled"]:
        raise HTTPException(400, "Node recovery is disabled")

    try:
        pod_recovery.approve_recovery(ctx["core"], ctx["custom"], body.recovery_id, body.approved_by)
        return {"status": "approved", "recovery_id": body.recovery_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@node_recovery_router.post("/cancel/{recovery_id}")
def cancel_route(recovery_id: str, ctx=Depends(get_k8s_context)):
    if not ctx:
        raise HTTPException(503, "Kubernetes connection not available")

    if not ctx["enabled"]:
        raise HTTPException(400, "Node recovery is disabled")

    try:
        pod_recovery.cancel_recovery(ctx["custom"], recovery_id)
        return {"status": "cancelled", "recovery_id": recovery_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@node_recovery_router.get("/enabled")
def get_recovery_enabled():
    config = get_clusters_config()
    return {
        "enabled": config.k8s.node_recovery.enabled,
        "k8s_enabled": config.k8s.enabled
    }
