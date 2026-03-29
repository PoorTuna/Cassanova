from pydantic import BaseModel


class CreateRoleRequest(BaseModel):
    username: str
    password: str | None = None
    superuser: bool = False
    login: bool = True


class EditRoleRequest(BaseModel):
    password: str | None = None
    superuser: bool | None = None
    login: bool | None = None


class PermissionRequest(BaseModel):
    role: str
    resource: str
    permission: str
