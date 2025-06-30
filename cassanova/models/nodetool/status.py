from pydantic import BaseModel, Field, ConfigDict


class NodeToolStatus(BaseModel):
    address: str
    load: str = Field(alias='disk_usage')
    tokens: str
    owns: str
    host_id: str
    dc: str
    rack: str
    status: str
    state: str

    model_config = ConfigDict(populate_by_name=True)
