from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, computed_field, Field, field_validator, ConfigDict


class Table(BaseModel):
    name: str
    partitions: Optional[int] = None
    size_on_disk: Optional[str] = None  # e.g. "12.3 MB"
    read_throughput: Optional[str] = None  # e.g. "123 req/s"
    write_throughput: Optional[str] = None


class Keyspace(BaseModel):
    name: str
    replication: str
    durable_writes: Optional[bool | str] = Field(default='N/A')
    virtual: Optional[bool] = Field(default=False)
    tables: List[Table]

    @computed_field
    @property
    def table_count(self) -> int:
        return len(self.tables)

    @field_validator('durable_writes', mode='before')
    def set_durable_writes_na(cls, v):
        if v is None:
            return "N/A"
        return v

    @field_validator('virtual', mode='before')
    def set_virtual_false(cls, v):
        if v is None:
            return False
        return v


class Node(BaseModel):
    name: str
    status: str
    load: Optional[str] = None  # e.g. "5.4 GB"
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    token_range: Optional[str] = None  # e.g. "0 - 567342342"


class ClusterEvent(BaseModel):
    timestamp: datetime
    message: str


class ClusterInfo(BaseModel):
    name: str = Field(alias='cluster')
    snitch: str
    version: str
    partitioner: Optional[str] = None
    nodes: List[Node] = []
    keyspaces: List[Keyspace] = []
    total_nodes: int
    up_nodes: int
    down_nodes: int
    status: str

    model_config = ConfigDict(populate_by_name=True)
