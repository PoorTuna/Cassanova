from pydantic import BaseModel, Field

from cassanova.config.ldap_config import LDAPConfig
from cassanova.models.auth_models import WebRole, WebUser, get_default_roles


class AuthConfig(BaseModel):
    enabled: bool = False
    secret_key: str = "insecure_default_secret_change_me"
    algorithm: str = "HS256"
    session_expire_minutes: int = 120
    users: list[WebUser] = Field(default_factory=list)
    roles: list[WebRole] = Field(default_factory=get_default_roles)
    ldap: LDAPConfig | None = None

    def get_user(self, username: str) -> WebUser | None:
        for user in self.users:
            if user.username == username:
                return user
        return None

    def get_role_permissions(self, role_name: str) -> list[str]:
        for role in self.roles:
            if role.name == role_name:
                return role.permissions
        return []
