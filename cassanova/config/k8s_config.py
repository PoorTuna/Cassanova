from typing import Optional
from pydantic import BaseModel, Field

from cassanova.config.node_recovery_config import NodeRecoveryConfig

class K8sConfig(BaseModel):
    enabled: bool = False
    kubeconfig: Optional[str] = None
    namespace: Optional[str] = None
    suffix: str = "-service"
    periodic_discovery_enabled: bool = Field(default=False, description="Enable periodic discovery of K8s clusters")
    discovery_interval_seconds: int = Field(default=60, description="Interval in seconds for periodic discovery")
    node_recovery: NodeRecoveryConfig = NodeRecoveryConfig()
