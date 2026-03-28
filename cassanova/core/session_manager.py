from logging import getLogger
from threading import Lock

from cassandra.cluster import Cluster, Session

from cassanova.config.cluster_config import ClusterConnectionConfig, generate_cluster_connection

logger = getLogger(__name__)


class SessionManager:
    _instances: dict[str, Cluster] = {}
    _sessions: dict[str, Session] = {}
    _lock = Lock()

    @classmethod
    def get_session(cls, cluster_name: str, cluster_config: ClusterConnectionConfig) -> Session:
        with cls._lock:
            if cluster_name not in cls._sessions:
                cluster = generate_cluster_connection(cluster_config)
                cls._instances[cluster_name] = cluster
                cls._sessions[cluster_name] = cluster.connect()

            return cls._sessions[cluster_name]

    @classmethod
    def shutdown_all(cls):
        with cls._lock:
            for name, session in cls._sessions.items():
                try:
                    session.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down session '{name}': {e}")
            for name, cluster in cls._instances.items():
                try:
                    cluster.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down cluster '{name}': {e}")
            cls._sessions.clear()
            cls._instances.clear()


session_manager = SessionManager()
