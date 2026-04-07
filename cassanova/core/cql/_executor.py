"""Central CQL execution function for all user-initiated mutations.

All mutation code paths route through ``execute_cql`` which enforces
read-only mode, RBAC permissions, and emits structured audit log lines.
Internal read-only system queries bypass this and use session.execute directly.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from cassandra.cluster import Session
from cassandra.query import BatchStatement, SimpleStatement

from cassanova.api.dependencies.auth import check_permission
from cassanova.config.cassanova_config import get_clusters_config
from cassanova.exceptions.cql_exceptions import CQLPermissionDenied, ReadOnlyClusterError
from cassanova.models.auth_models import WebUser

_audit_logger = logging.getLogger("cassanova.audit")
if not _audit_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(_handler)
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False

_MUTATION_PREFIXES = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "GRANT", "REVOKE", "BATCH",
})

_ADMIN_KEYWORDS = frozenset({"DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"})
_WRITE_KEYWORDS = frozenset({"INSERT", "UPDATE", "DELETE", "BATCH"})


def _is_mutation(statement: SimpleStatement | BatchStatement | str) -> bool:
    return _detect_action(statement) in _MUTATION_PREFIXES


def execute_cql(
    session: Session,
    statement: SimpleStatement | BatchStatement | str,
    cluster_name: str,
    user: WebUser | None,
    parameters: tuple | list | None = None,
    **execute_kwargs: Any,
) -> Any:
    action = _detect_action(statement)
    if action not in _MUTATION_PREFIXES:
        return session.execute(statement, parameters, **execute_kwargs)

    config = get_clusters_config()
    cluster_config = config.clusters.get(cluster_name)
    if cluster_config and cluster_config.read_only:
        raise ReadOnlyClusterError(cluster_name)

    required_perm = "cluster:admin" if action in _ADMIN_KEYWORDS else "cluster:write"
    if not check_permission(user, required_perm):
        username = user.username if user else "anonymous"
        raise CQLPermissionDenied(username, cluster_name, required_perm)

    _audit_log(user, cluster_name, statement, action, parameters is not None)

    return session.execute(statement, parameters, **execute_kwargs)


def _detect_action(statement: SimpleStatement | BatchStatement | str) -> str:
    if isinstance(statement, BatchStatement):
        return "BATCH"
    query = statement.query_string if isinstance(statement, SimpleStatement) else str(statement)
    first_word = query.strip().split()[0].upper() if query and query.strip() else ""
    return first_word


def _audit_log(
    user: WebUser | None, cluster_name: str, statement: Any, action: str, has_params: bool
) -> None:
    query_str = (
        "<BatchStatement>"
        if isinstance(statement, BatchStatement)
        else (statement.query_string if isinstance(statement, SimpleStatement) else str(statement))
    )
    _audit_logger.info(
        json.dumps({
            "timestamp": datetime.now(UTC).isoformat(),
            "user": user.username if user else "anonymous",
            "cluster": cluster_name,
            "action": action,
            "query": query_str[:2000],
            "has_params": has_params,
        })
    )
