class ReadOnlyClusterError(Exception):
    def __init__(self, cluster_name: str) -> None:
        self.cluster_name = cluster_name
        super().__init__(f"Cluster '{cluster_name}' is in read-only mode")


class CQLPermissionDenied(Exception):
    def __init__(self, username: str, cluster_name: str, required_permission: str) -> None:
        self.username = username
        self.cluster_name = cluster_name
        self.required_permission = required_permission
        super().__init__(
            f"User '{username}' lacks '{required_permission}' on cluster '{cluster_name}'"
        )
