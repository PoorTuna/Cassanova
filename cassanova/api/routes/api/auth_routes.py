from re import match

from fastapi import APIRouter, HTTPException

from cassanova.api.dependencies.db_session import get_session
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest, PermissionRequest

auth_router = APIRouter()


@auth_router.get("/cluster/{cluster_name}/auth/roles")
def get_roles(cluster_name: str):
    session = get_session(cluster_name)
    try:
        rows = session.execute("SELECT role, is_superuser, can_login FROM system_auth.roles")
        return [
            {
                "role": row.role,
                "is_superuser": row.is_superuser,
                "can_login": row.can_login
            }
            for row in rows
        ]
    except Exception as e:
        if "Table 'system_auth.roles' not found" in str(e) or "unauthorized" in str(e).lower():
            return []
        raise HTTPException(status_code=500, detail=f"Failed to fetch roles: {e}")


@auth_router.post("/cluster/{cluster_name}/auth/roles")
def create_role(cluster_name: str, request: CreateRoleRequest):
    session = get_session(cluster_name)
    try:
        if not match(r"^[a-zA-Z0-9_\-]+$", request.username):
            raise ValueError("Username contains invalid characters (only alphanumeric, _ and - allowed)")

        options = [
            f"LOGIN = {str(request.login).lower()}",
            f"SUPERUSER = {str(request.superuser).lower()}"
        ]
        cql_params = []
        if request.password:
            options.append("PASSWORD = %s")
            cql_params.append(request.password)

        final_cql = f'CREATE ROLE IF NOT EXISTS "{request.username}" WITH {" AND ".join(options)}'

        try:
            session.execute(final_cql, tuple(cql_params))
        except Exception as db_err:
            if "doesn't support PASSWORD" in str(db_err) and request.password:
                fallback_opts = [o for o in options if "PASSWORD" not in o]
                fallback_cql = f'CREATE ROLE IF NOT EXISTS "{request.username}" WITH {(" AND ".join(fallback_opts))}'
                session.execute(fallback_cql)
                return {"message": f"Role {request.username} created (Password ignored by server setting)"}
            raise db_err

        return {"message": f"Role {request.username} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.put("/cluster/{cluster_name}/auth/roles/{role_name}")
def edit_role(cluster_name: str, role_name: str, request: EditRoleRequest):
    session = get_session(cluster_name)
    try:
        if not match(r"^[a-zA-Z0-9_\-]+$", role_name):
            raise ValueError("Invalid role name")

        changes = []
        params = []

        if request.password is not None:
            changes.append("PASSWORD = %s")
            params.append(request.password)

        if request.superuser is not None:
            changes.append(f"SUPERUSER = {str(request.superuser).lower()}")

        if request.login is not None:
            changes.append(f"LOGIN = {str(request.login).lower()}")

        if not changes:
            return {"message": "No changes requested"}

        cql = f'ALTER ROLE "{role_name}" WITH {(" AND ".join(changes))}'
        session.execute(cql, tuple(params))
        return {"message": f"Role {role_name} updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.delete("/cluster/{cluster_name}/auth/roles/{role_name}")
def delete_role(cluster_name: str, role_name: str):
    session = get_session(cluster_name)
    try:
        if not match(r"^[a-zA-Z0-9_\-]+$", role_name):
            raise ValueError("Invalid role name")

        session.execute(f'DROP ROLE IF EXISTS "{role_name}"')
        return {"message": f"Role {role_name} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.get("/cluster/{cluster_name}/auth/permissions/{role_name}")
def get_permissions(cluster_name: str, role_name: str):
    session = get_session(cluster_name)
    try:
        rows = session.execute(f'LIST ALL PERMISSIONS OF "{role_name}"')
        return [{"resource": row.resource, "permission": row.permission} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth_router.post("/cluster/{cluster_name}/auth/permissions/grant")
def grant_permission(cluster_name: str, request: PermissionRequest):
    session = get_session(cluster_name)
    try:
        cql = f'GRANT {request.permission} ON {request.resource} TO "{request.role}"'
        session.execute(cql)
        return {"message": f"Granted {request.permission} on {request.resource} to {request.role}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/cluster/{cluster_name}/auth/permissions/revoke")
def revoke_permission(cluster_name: str, request: PermissionRequest):
    session = get_session(cluster_name)
    try:
        cql = f'REVOKE {request.permission} ON {request.resource} FROM "{request.role}"'
        session.execute(cql)
        return {"message": f"Revoked {request.permission} on {request.resource} from {request.role}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
