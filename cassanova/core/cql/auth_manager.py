from re import match

from cassandra.cluster import Session

from cassanova.core.cql.sanitize_input import sanitize_identifier
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest

_VALID_PERMISSIONS = frozenset(
    {
        "ALL PERMISSIONS",
        "ALTER",
        "AUTHORIZE",
        "CREATE",
        "DESCRIBE",
        "DROP",
        "EXECUTE",
        "MODIFY",
        "SELECT",
    }
)

_VALID_RESOURCE_PREFIXES = frozenset(
    {
        "ALL KEYSPACES",
        "ALL TABLES",
        "ALL ROLES",
        "ALL FUNCTIONS",
        "ALL MBEANS",
        "KEYSPACE",
        "TABLE",
        "ROLE",
        "FUNCTION",
        "MBEAN",
    }
)


def validate_role_name(name: str) -> None:
    if not match(r"^[a-zA-Z0-9_\-]+$", name):
        raise ValueError(
            "Role/Username contains invalid characters (only alphanumeric, _ and - allowed)"
        )


def _validate_permission(permission: str) -> None:
    if permission.upper() not in _VALID_PERMISSIONS:
        raise ValueError(f"Invalid permission: {permission}")


def _validate_resource(resource: str) -> None:
    upper = resource.strip().upper()
    if upper in ("ALL KEYSPACES", "ALL TABLES", "ALL ROLES", "ALL FUNCTIONS", "ALL MBEANS"):
        return

    parts = resource.strip().split(None, 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid resource format: {resource}")

    prefix = parts[0].upper()
    if prefix not in ("KEYSPACE", "TABLE", "ROLE", "FUNCTION", "MBEAN"):
        raise ValueError(f"Invalid resource type: {prefix}")

    identifiers = parts[1].split(".")
    for identifier in identifiers:
        clean = identifier.strip().strip('"')
        sanitize_identifier(clean)


def get_all_roles(session: Session) -> list[dict]:
    try:
        rows = session.execute("SELECT role, is_superuser, can_login FROM system_auth.roles")
        return [
            {"role": row.role, "is_superuser": row.is_superuser, "can_login": row.can_login}
            for row in rows
        ]
    except Exception as e:
        if "Table 'system_auth.roles' not found" in str(e) or "unauthorized" in str(e).lower():
            return []
        raise e


def create_role(session: Session, request: CreateRoleRequest) -> str:
    validate_role_name(request.username)

    options = [
        f"LOGIN = {str(request.login).lower()}",
        f"SUPERUSER = {str(request.superuser).lower()}",
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
            fallback_cql = (
                f'CREATE ROLE IF NOT EXISTS "{request.username}" WITH {" AND ".join(fallback_opts)}'
            )
            session.execute(fallback_cql)
            return f"Role {request.username} created (Password ignored by server setting)"
        raise db_err


def alter_role(session: Session, role_name: str, request: EditRoleRequest) -> str:
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


def drop_role(session: Session, role_name: str) -> str:
    validate_role_name(role_name)
    session.execute(f'DROP ROLE IF EXISTS "{role_name}"')
    return f"Role {role_name} deleted"


def list_permissions(session: Session, role_name: str) -> list[dict[str, str]]:
    validate_role_name(role_name)
    rows = session.execute(f'LIST ALL PERMISSIONS OF "{role_name}"')
    return [{"resource": row.resource, "permission": row.permission} for row in rows]


def grant_permission(session: Session, permission: str, resource: str, role: str) -> str:
    _validate_permission(permission)
    _validate_resource(resource)
    validate_role_name(role)
    cql = f'GRANT {permission} ON {resource} TO "{role}"'
    session.execute(cql)
    return f"Granted {permission} on {resource} to {role}"


def revoke_permission(session: Session, permission: str, resource: str, role: str) -> str:
    _validate_permission(permission)
    _validate_resource(resource)
    validate_role_name(role)
    cql = f'REVOKE {permission} ON {resource} FROM "{role}"'
    session.execute(cql)
    return f"Revoked {permission} on {resource} from {role}"
