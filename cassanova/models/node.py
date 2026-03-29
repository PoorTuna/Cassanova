from typing import Annotated, Literal

from cassandra.cqltypes import UUID
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


class NodeInfo(BaseModel):
    host_id: Annotated[str | UUID, BeforeValidator(lambda v: str(v))]
    data_center: str | None = None
    rack: str | None = None
    release_version: str | None = None
    schema_version: Annotated[
        str | UUID | None,
        BeforeValidator(lambda v: str(v) if v else None),
    ] = None
    tokens: Annotated[list[int], BeforeValidator(lambda v: list(v) if v else [])]
    broadcast_address: str | None = Field(default=None, alias="peer")
    broadcast_port: int | None = Field(default=None, alias="peer_port")
    listen_address: str | None = None
    listen_port: int | None = None
    preferred_ip: str | None = None
    preferred_port: int | None = None
    rpc_address: str | None = Field(default=None, alias="native_address")
    rpc_port: int | None = Field(default=None, alias="native_port")
    key: str | None = None
    bootstrapped: Literal["COMPLETED", "IN_PROGRESS", "FAILED", "NONE"] | None = None
    cluster_name: str | None = None
    cql_version: str | None = None
    gossip_generation: int | None = None
    native_protocol_version: int | None = None
    partitioner: str | None = None
    truncated_at: Annotated[
        dict[str, str] | None,
        BeforeValidator(
            lambda value: {str(k): v.hex() for k, v in dict(value).items()} if value else {}
        ),
    ] = None

    model_config = ConfigDict(populate_by_name=True)
