from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from cassanova.core.auth_utils import hash_password


class WebRole(BaseModel):
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class WebUser(BaseModel):
    username: str
    password: Annotated[str, BeforeValidator(hash_password)]
    roles: list[str] = Field(default_factory=list)
    full_name: str | None = None


def get_default_roles() -> list["WebRole"]:
    return [
        WebRole(name="admin", permissions=["*"]),
        WebRole(name="viewer", permissions=["cluster:view", "data:read"]),
    ]
