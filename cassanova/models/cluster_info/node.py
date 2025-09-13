from typing import Annotated, Literal

from cassandra.cqltypes import UUID
from pydantic import BaseModel, BeforeValidator


class NodeInfo(BaseModel):
    key: str
    bootstrapped: Literal["COMPLETED", "IN_PROGRESS", "FAILED", "NONE"]
    broadcast_address: str
    broadcast_port: int
    cluster_name: str
    cql_version: str
    data_center: str
    gossip_generation: int

    host_id: Annotated[str | UUID, BeforeValidator(lambda v: str(v))]
    listen_address: str
    listen_port: int
    native_protocol_version: int
    partitioner: str
    rack: str
    release_version: str
    rpc_address: str
    rpc_port: int
    schema_version: Annotated[str | UUID, BeforeValidator(lambda v: str(v))]
    tokens: Annotated[list[int], BeforeValidator(lambda v: v or [])]
    truncated_at: Annotated[
        dict[str, str],
        BeforeValidator(lambda v: {str(k): val.hex() for k, val in dict(v).items()} if v else {}),
    ]
