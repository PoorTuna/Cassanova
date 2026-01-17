from re import match
from cassandra.cluster import Session
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest

def validate_role_name(name: str):
    if not match(r"^[a-zA-Z0-9_\-]+$", name):
        raise ValueError("Role/Username contains invalid characters (only alphanumeric, _ and - allowed)")

def get_all_roles(session: Session) -> list[dict]:
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
        raise e

def create_role(session: Session, request: CreateRoleRequest):
    validate_role_name(request.username)
    
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
        return f"Role {request.username} created successfully"
    except Exception as db_err:
        if "doesn't support PASSWORD" in str(db_err) and request.password:
            fallback_opts = [o for o in options if "PASSWORD" not in o]
            fallback_cql = f'CREATE ROLE IF NOT EXISTS "{request.username}" WITH {(" AND ".join(fallback_opts))}'
            session.execute(fallback_cql)
            return f"Role {request.username} created (Password ignored by server setting)"
        raise db_err

def alter_role(session: Session, role_name: str, request: EditRoleRequest):
    validate_role_name(role_name)
    
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
        return "No changes requested"

    cql = f'ALTER ROLE "{role_name}" WITH {(" AND ".join(changes))}'
    session.execute(cql, tuple(params))
    return f"Role {role_name} updated"

def drop_role(session: Session, role_name: str):
    validate_role_name(role_name)
    session.execute(f'DROP ROLE IF EXISTS "{role_name}"')
    return f"Role {role_name} deleted"

def list_permissions(session: Session, role_name: str):
    rows = session.execute(f'LIST ALL PERMISSIONS OF "{role_name}"')
    return [{"resource": row.resource, "permission": row.permission} for row in rows]

def grant_permission(session: Session, permission: str, resource: str, role: str):
    cql = f'GRANT {permission} ON {resource} TO "{role}"'
    session.execute(cql)
    return f"Granted {permission} on {resource} to {role}"

def revoke_permission(session: Session, permission: str, resource: str, role: str):
    cql = f'REVOKE {permission} ON {resource} FROM "{role}"'
    session.execute(cql)
    return f"Revoked {permission} on {resource} from {role}"
