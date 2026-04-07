from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from cassanova.api.dependencies.auth import require_permission
from cassanova.api.dependencies.db_session import get_session
from cassanova.core.cql.auth_manager import (
    alter_role,
    create_role,
    drop_role,
    get_all_roles,
    grant_permission,
    list_permissions,
    revoke_permission,
)
from cassanova.models.auth_models import WebUser
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest, PermissionRequest

auth_router = APIRouter()


@auth_router.get("/cluster/{cluster_name}/auth/roles")
def get_roles(cluster_name: str) -> list[dict[str, Any]]:
    session = get_session(cluster_name)
    try:
        return get_all_roles(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch roles: {e}") from e


@auth_router.post("/cluster/{cluster_name}/auth/roles")
def create_role_route(
    cluster_name: str,
    request: CreateRoleRequest,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> dict[str, str]:
    session = get_session(cluster_name)
    try:
        message = create_role(session, request, cluster_name, _user)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@auth_router.put("/cluster/{cluster_name}/auth/roles/{role_name}")
def edit_role_route(
    cluster_name: str,
    role_name: str,
    request: EditRoleRequest,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> dict[str, str]:
    session = get_session(cluster_name)
    try:
        message = alter_role(session, role_name, request, cluster_name, _user)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@auth_router.delete("/cluster/{cluster_name}/auth/roles/{role_name}")
def delete_role_route(
    cluster_name: str, role_name: str, _user: WebUser = Depends(require_permission("cluster:admin"))
) -> dict[str, str]:
    session = get_session(cluster_name)
    try:
        message = drop_role(session, role_name, cluster_name, _user)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@auth_router.get("/cluster/{cluster_name}/auth/permissions/{role_name}")
def get_permissions_route(cluster_name: str, role_name: str) -> list[dict[str, str]]:
    session = get_session(cluster_name)
    try:
        return list_permissions(session, role_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@auth_router.post("/cluster/{cluster_name}/auth/permissions/grant")
def grant_permission_route(
    cluster_name: str,
    request: PermissionRequest,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> dict[str, str]:
    session = get_session(cluster_name)
    try:
        message = grant_permission(
            session, request.permission, request.resource, request.role, cluster_name, _user
        )
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@auth_router.post("/cluster/{cluster_name}/auth/permissions/revoke")
def revoke_permission_route(
    cluster_name: str,
    request: PermissionRequest,
    _user: WebUser = Depends(require_permission("cluster:admin")),
) -> dict[str, str]:
    session = get_session(cluster_name)
    try:
        message = revoke_permission(
            session, request.permission, request.resource, request.role, cluster_name, _user
        )
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
