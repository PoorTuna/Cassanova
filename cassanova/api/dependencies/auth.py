from datetime import datetime, timedelta
from typing import Optional, NoReturn

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from cassanova.config.cassanova_config import get_clusters_config, CassanovaConfig
from cassanova.core.auth_utils import verify_password
from cassanova.exceptions.auth_exceptions import LoginRequired
from cassanova.models.auth_models import WebUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login", auto_error=False)


def get_config() -> CassanovaConfig:
    return get_clusters_config()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    config = get_config()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.auth.session_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.auth.secret_key, algorithm=config.auth.algorithm)
    return encoded_jwt


async def get_current_user(
        request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> Optional[WebUser]:
    config = get_config()

    if not config.auth.enabled:
        return WebUser(username="anonymous", password="none", roles=["admin"])

    if not isinstance(token, str):
        token = None

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = jwt.decode(token, config.auth.secret_key, algorithms=[config.auth.algorithm])
        username: str = payload.get("sub")

        if not username:
            return None

        user = config.auth.get_user(username)
        return user
    except JWTError:
        return None


async def require_user(user: Optional[WebUser] = Depends(get_current_user)) -> WebUser | NoReturn:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_web_user(request: Request, user: Optional[WebUser] = Depends(get_current_user)) -> WebUser | NoReturn:
    if not user:
        raise LoginRequired()
    return user


def check_permission(user: Optional[WebUser], required_perm: str) -> bool:
    config = get_config()
    if not config.auth.enabled:
        return True

    if user is None:
        return False

    user_perms = {perm for role in user.roles for perm in config.auth.get_role_permissions(role)}

    if "*" in user_perms:
        return True

    if required_perm in user_perms:
        return True

    required_parts = required_perm.split(":")
    for perm in user_perms:
        if perm.endswith("*"):
            parts = perm.split(":")
            if len(parts) == 2 and parts[1] == "*" and parts[0] == required_parts[0]:
                return True

    return False


def require_permission(perm: str) -> WebUser | NoReturn:
    async def _check_permission_dependency(user: WebUser = Depends(require_user)):
        if not check_permission(user, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {perm}"
            )
        return user

    return _check_permission_dependency


def authenticate_user(username: str, password: str) -> Optional[WebUser]:
    config = get_clusters_config()
    user = config.auth.get_user(username)
    if not user or not verify_password(password, user.password):
        return None
    return user
