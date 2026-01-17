from typing import Optional, Annotated

from passlib.context import CryptContext
from pydantic import BaseModel, Field, AfterValidator

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class WebRole(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class WebUser(BaseModel):
    username: str
    password: Annotated[
        str,
        AfterValidator(lambda v: v if v.startswith("$2b$") or v.startswith("$2a$") else pwd_context.hash(v))
    ]
    roles: list[str] = Field(default_factory=list)
    full_name: Optional[str] = None


class AuthConfig(BaseModel):
    enabled: bool = False
    secret_key: str = "insecure_default_secret_change_me"
    algorithm: str = "HS256"
    session_expire_minutes: int = 120
    users: list[WebUser] = Field(default_factory=list)
    roles: list[WebRole] = Field(default_factory=list)

    def get_user(self, username: str) -> Optional[WebUser]:
        for user in self.users:
            if user.username == username:
                return user
        return None

    def get_role_permissions(self, role_name: str) -> list[str]:
        for role in self.roles:
            if role.name == role_name:
                return role.permissions
        return []
