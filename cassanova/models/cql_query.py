from cassandra import ConsistencyLevel
from pydantic import BaseModel, Field


class CQLQuery(BaseModel):
    cql: str
    cl: int = Field(default=ConsistencyLevel.QUORUM)
    enable_tracing: bool = False
