from pydantic import BaseModel, Field

class RemediationConfig(BaseModel):
    enabled: bool = False
    auto_poll_enabled: bool = True
    poll_interval_seconds: int = 30
    max_concurrent_per_dc: int = 1
    max_concurrent_per_rack: int = 10
