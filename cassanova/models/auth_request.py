from typing import Optional

from pydantic import BaseModel


class CreateRoleRequest(BaseModel):
    username: str
    password: Optional[str] = None
    superuser: bool = False
    login: bool = True


class EditRoleRequest(BaseModel):
    password: Optional[str] = None
    superuser: Optional[bool] = None
    login: Optional[bool] = None


class PermissionRequest(BaseModel):
    role: str
    resource: str
    permission: str
