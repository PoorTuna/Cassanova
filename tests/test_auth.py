from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from jose import jwt

from cassanova.api.dependencies.auth import (
    create_access_token,
    check_permission,
)
from cassanova.config.auth_config import AuthConfig
from cassanova.models.auth_models import WebUser, WebRole


def _make_config(**overrides):
    defaults = dict(
        enabled=True,
        secret_key="test_secret_key_for_unit_tests",
        algorithm="HS256",
        session_expire_minutes=60,
        users=[],
        roles=[
            WebRole(name="admin", permissions=["*"]),
            WebRole(name="viewer", permissions=["cluster:view", "data:read"]),
            WebRole(name="editor", permissions=["cluster:view", "cluster:write", "data:read", "data:write"]),
        ],
    )
    defaults.update(overrides)
    return AuthConfig(**defaults)


def _make_cassanova_config(**auth_overrides):
    config = MagicMock()
    config.auth = _make_config(**auth_overrides)
    return config


class TestCreateAccessToken:
    @patch("cassanova.api.dependencies.auth.get_config")
    def test_creates_valid_jwt(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        token = create_access_token({"sub": "alice", "roles": ["admin"]})
        payload = jwt.decode(token, "test_secret_key_for_unit_tests", algorithms=["HS256"])
        assert payload["sub"] == "alice"
        assert "exp" in payload

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_custom_expiration(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        token = create_access_token(
            {"sub": "alice"}, expires_delta=timedelta(minutes=5)
        )
        payload = jwt.decode(token, "test_secret_key_for_unit_tests", algorithms=["HS256"])
        assert payload["sub"] == "alice"


class TestCheckPermission:
    @patch("cassanova.api.dependencies.auth.get_config")
    def test_auth_disabled_always_passes(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config(enabled=False)
        assert check_permission(None, "anything") is True

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_none_user_denied(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        assert check_permission(None, "cluster:view") is False

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_admin_wildcard_passes(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        user = WebUser(username="admin", password="x", roles=["admin"])
        assert check_permission(user, "anything:here") is True

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_viewer_has_read(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        user = WebUser(username="bob", password="x", roles=["viewer"])
        assert check_permission(user, "data:read") is True

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_viewer_denied_write(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        user = WebUser(username="bob", password="x", roles=["viewer"])
        assert check_permission(user, "cluster:write") is False

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_exact_permission_match(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        user = WebUser(username="editor", password="x", roles=["editor"])
        assert check_permission(user, "cluster:write") is True

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_unknown_role_gets_no_permissions(self, mock_get_config):
        mock_get_config.return_value = _make_cassanova_config()
        user = WebUser(username="ghost", password="x", roles=["nonexistent"])
        assert check_permission(user, "cluster:view") is False


class TestJwtRoleTrust:
    @patch("cassanova.api.dependencies.auth.get_config")
    def test_jwt_unknown_roles_dropped(self, mock_get_config):
        """Roles claimed in JWT that don't exist in config should be rejected."""
        config = _make_cassanova_config()
        mock_get_config.return_value = config

        token = jwt.encode(
            {"sub": "attacker", "roles": ["admin", "fake_superadmin"]},
            "test_secret_key_for_unit_tests",
            algorithm="HS256",
        )

        from cassanova.api.dependencies.auth import get_current_user

        import asyncio

        request = MagicMock()
        request.headers.get.return_value = None
        request.cookies.get.return_value = None

        user = asyncio.get_event_loop().run_until_complete(
            get_current_user(request, token)
        )

        assert user is not None
        assert "admin" in user.roles
        assert "fake_superadmin" not in user.roles

    @patch("cassanova.api.dependencies.auth.get_config")
    def test_jwt_all_unknown_roles_returns_none(self, mock_get_config):
        """If ALL JWT roles are unknown, user should be None."""
        config = _make_cassanova_config()
        mock_get_config.return_value = config

        token = jwt.encode(
            {"sub": "attacker", "roles": ["fake_role1", "fake_role2"]},
            "test_secret_key_for_unit_tests",
            algorithm="HS256",
        )

        from cassanova.api.dependencies.auth import get_current_user

        import asyncio

        request = MagicMock()
        request.headers.get.return_value = None
        request.cookies.get.return_value = None

        user = asyncio.get_event_loop().run_until_complete(
            get_current_user(request, token)
        )

        assert user is None
