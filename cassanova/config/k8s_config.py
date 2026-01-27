from typing import Optional
from pydantic import BaseModel, Field

from cassanova.config.node_recovery_config import NodeRecoveryConfig

class K8sConfig(BaseModel):
    enabled: bool = False
    kubeconfig: Optional[str] = None
    namespace: Optional[str] = None
    suffix: str = "-service"
    node_recovery: NodeRecoveryConfig = NodeRecoveryConfig()
