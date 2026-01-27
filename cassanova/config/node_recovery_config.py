from pydantic import BaseModel


class NodeRecoveryConfig(BaseModel):
    enabled: bool = False
