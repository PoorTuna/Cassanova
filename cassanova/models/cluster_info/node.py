from typing import Annotated, Literal, Optional

from cassandra.cqltypes import UUID
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict


class NodeInfo(BaseModel):
    host_id: Annotated[str | UUID, BeforeValidator(lambda v: str(v))]
    data_center: Optional[str] = None
    rack: Optional[str] = None
    release_version: Optional[str] = None
    schema_version: Annotated[
        Optional[str | UUID],
        BeforeValidator(lambda v: str(v) if v else None),
    ] = None
    tokens: Annotated[list[int], BeforeValidator(lambda v: v or [])]
    broadcast_address: Optional[str] = Field(default=None, alias="peer")
    broadcast_port: Optional[int] = Field(default=None, alias="peer_port")
    listen_address: Optional[str] = None
    listen_port: Optional[int] = None
    preferred_ip: Optional[str] = None
    preferred_port: Optional[int] = None
    rpc_address: Optional[str] = Field(default=None, alias="native_address")
    rpc_port: Optional[int] = Field(default=None, alias="native_port")
    key: Optional[str] = None
    bootstrapped: Optional[Literal["COMPLETED", "IN_PROGRESS", "FAILED", "NONE"]] = None
    cluster_name: Optional[str] = None
    cql_version: Optional[str] = None
    gossip_generation: Optional[int] = None
    native_protocol_version: Optional[int] = None
    partitioner: Optional[str] = None
    truncated_at: Annotated[
        Optional[dict[str, str]],
        BeforeValidator(lambda value: {str(k): v.hex() for k, v in dict(value).items()} if value else {})] = None

    model_config = ConfigDict(populate_by_name=True)
