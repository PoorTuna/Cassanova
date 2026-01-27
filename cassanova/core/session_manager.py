from cassandra.cluster import Cluster, Session

from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection


class SessionManager:
    _instances: dict[str, Cluster] = {}
    _sessions: dict[str, Session] = {}

    @classmethod
    def get_session(cls, cluster_name: str, cluster_config: ClusterConnectionConfig) -> Session:
        if cluster_name not in cls._sessions:
            cluster = generate_cluster_connection(cluster_config)
            cls._instances[cluster_name] = cluster
            cls._sessions[cluster_name] = cluster.connect()

        return cls._sessions[cluster_name]

    @classmethod
    def shutdown_all(cls):
        for session in cls._sessions.values():
            try:
                session.shutdown()
            except:
                pass
        for cluster in cls._instances.values():
            try:
                cluster.shutdown()
            except:
                pass
        cls._sessions.clear()
        cls._instances.clear()


session_manager = SessionManager()
