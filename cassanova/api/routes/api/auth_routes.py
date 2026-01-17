from fastapi import APIRouter, HTTPException

from cassanova.api.dependencies.db_session import get_session
from cassanova.core.cql.auth_manager import (
    get_all_roles, create_role, alter_role, drop_role, 
    list_permissions, grant_permission, revoke_permission
)
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest, PermissionRequest

auth_router = APIRouter()


@auth_router.get("/cluster/{cluster_name}/auth/roles")
def get_roles(cluster_name: str):
    session = get_session(cluster_name)
    try:
        return get_all_roles(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch roles: {e}")


@auth_router.post("/cluster/{cluster_name}/auth/roles")
def create_role_route(cluster_name: str, request: CreateRoleRequest):
    session = get_session(cluster_name)
    try:
        message = create_role(session, request)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.put("/cluster/{cluster_name}/auth/roles/{role_name}")
def edit_role_route(cluster_name: str, role_name: str, request: EditRoleRequest):
    session = get_session(cluster_name)
    try:
        message = alter_role(session, role_name, request)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.delete("/cluster/{cluster_name}/auth/roles/{role_name}")
def delete_role_route(cluster_name: str, role_name: str):
    session = get_session(cluster_name)
    try:
        message = drop_role(session, role_name)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.get("/cluster/{cluster_name}/auth/permissions/{role_name}")
def get_permissions_route(cluster_name: str, role_name: str):
    session = get_session(cluster_name)
    try:
        return list_permissions(session, role_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.post("/cluster/{cluster_name}/auth/permissions/grant")
def grant_permission_route(cluster_name: str, request: PermissionRequest):
    session = get_session(cluster_name)
    try:
        message = grant_permission(session, request.permission, request.resource, request.role)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/cluster/{cluster_name}/auth/permissions/revoke")
def revoke_permission_route(cluster_name: str, request: PermissionRequest):
    session = get_session(cluster_name)
    try:
        message = revoke_permission(session, request.permission, request.resource, request.role)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
