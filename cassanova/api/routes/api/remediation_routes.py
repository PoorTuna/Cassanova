from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from cassanova.config.cassanova_config import get_clusters_config

remediation_router = APIRouter(prefix='/remediation', tags=['Remediation'])


def get_remediation_service(request: Request):
    if hasattr(request.app.state, "remediation_service"):
        return request.app.state.remediation_service
    return None


class ApproveRequest(BaseModel):
    remediation_id: str
    approved_by: str


class TriggerRequest(BaseModel):
    node_name: str


@remediation_router.get("/status")
def get_remediation_status(service=Depends(get_remediation_service)):
    if not service:
        raise HTTPException(503, "Remediation service not running")
    
    return service.get_status()


@remediation_router.post("/approve")
def approve_remediation(body: ApproveRequest, service=Depends(get_remediation_service)):
    if not service:
        raise HTTPException(503, "Remediation service not running")
    
    try:
        service.approve_remediation(body.remediation_id, body.approved_by)
        return {"status": "approved", "remediation_id": body.remediation_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@remediation_router.post("/cancel/{remediation_id}")
def cancel_remediation(remediation_id: str, service=Depends(get_remediation_service)):
    if not service:
        raise HTTPException(503, "Remediation service not running")
    
    try:
        service.cancel_remediation(remediation_id)
        return {"status": "cancelled", "remediation_id": remediation_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@remediation_router.post("/scan")
def scan_remediation(service=Depends(get_remediation_service)):
    if not service:
        raise HTTPException(503, "Remediation service not running")
    
    try:
        return service.scan_now()
    except Exception as e:
        raise HTTPException(500, str(e))





@remediation_router.get("/enabled")
def get_remediation_enabled():
    """Check if remediation feature is enabled"""
    config = get_clusters_config()
    return {
        "enabled": config.remediation.enabled,
        "k8s_enabled": config.k8s.enabled
    }
