from typing import Optional
from pydantic import BaseModel, Field

class K8sDiscoveryConfig(BaseModel):
    enabled: bool = False
    kubeconfig: Optional[str] = None
    namespace: Optional[str] = None
    suffix: str = "-service"
