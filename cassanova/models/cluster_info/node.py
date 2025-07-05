from typing import Optional

from pydantic import BaseModel


class NodeInfo(BaseModel):
    name: str
    status: str
    load: Optional[str] = None
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    token_range: Optional[str] = None
