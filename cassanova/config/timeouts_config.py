from pydantic import BaseModel, Field


class TimeoutConfig(BaseModel):
    """Query and connection timeouts in seconds.

    Applied globally to every Cassandra session so that a single bad query
    cannot hang a request indefinitely. Per-call overrides (e.g. DDL, batch
    imports) use the longer values defined here.
    """

    default_query: float = Field(default=30.0, gt=0)
    connect: float = Field(default=10.0, gt=0)
    ddl: float = Field(default=120.0, gt=0)
    batch: float = Field(default=120.0, gt=0)
    health_check: float = Field(default=5.0, gt=0)
