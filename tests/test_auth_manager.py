from unittest.mock import MagicMock

import pytest

from cassanova.core.cql.auth_manager import (
    _validate_permission,
    _validate_resource,
    alter_role,
    create_role,
    drop_role,
    grant_permission,
    list_permissions,
    revoke_permission,
    validate_role_name,
)
from cassanova.models.auth_request import CreateRoleRequest, EditRoleRequest


class TestValidateRoleName:
    @pytest.mark.parametrize("name", ["admin", "user_1", "my-role", "Role123"])
    def test_valid_names(self, name):
        validate_role_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "admin; DROP",
            "role name",
            "role'--",
            'role"',
            "role()",
            "",
        ],
    )
    def test_invalid_names_rejected(self, name):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_role_name(name)


class TestValidatePermission:
    @pytest.mark.parametrize(
        "perm",
        [
            "SELECT",
            "MODIFY",
            "ALTER",
            "CREATE",
            "DROP",
            "AUTHORIZE",
            "DESCRIBE",
            "EXECUTE",
            "ALL PERMISSIONS",
        ],
    )
    def test_valid_permissions(self, perm):
        _validate_permission(perm)

    @pytest.mark.parametrize(
        "perm",
        [
            "SELECT; DROP TABLE",
            "INVALID",
            "READ",
            "WRITE",
            "",
        ],
    )
    def test_invalid_permissions_rejected(self, perm):
        with pytest.raises(ValueError, match="Invalid permission"):
            _validate_permission(perm)


class TestValidateResource:
    @pytest.mark.parametrize(
        "resource",
        [
            "ALL KEYSPACES",
            "ALL TABLES",
            "ALL ROLES",
            "KEYSPACE my_ks",
            "TABLE my_ks.my_table",
            "ROLE admin",
        ],
    )
    def test_valid_resources(self, resource):
        _validate_resource(resource)

    def test_invalid_resource_type(self):
        with pytest.raises(ValueError, match="Invalid resource type"):
            _validate_resource("INVALID my_ks")

    def test_injection_in_resource_identifier(self):
        with pytest.raises(ValueError, match="Invalid CQL identifier"):
            _validate_resource("KEYSPACE my_ks; DROP TABLE foo")

    def test_empty_resource(self):
        with pytest.raises((ValueError, IndexError)):
            _validate_resource("")


class TestCreateRole:
    def test_creates_role_without_password(self, mock_session):
        request = CreateRoleRequest(username="new_user", login=True, superuser=False)
        result = create_role(mock_session, request)
        assert "created successfully" in result
        executed_cql = mock_session.execute.call_args[0][0]
        assert "new_user" in executed_cql
        assert "LOGIN = true" in executed_cql

    def test_creates_role_with_password(self, mock_session):
        request = CreateRoleRequest(
            username="new_user", password="secret123", login=True, superuser=False
        )
        create_role(mock_session, request)
        executed_cql = mock_session.execute.call_args[0][0]
        assert "PASSWORD = %s" in executed_cql
        params = mock_session.execute.call_args[0][1]
        assert "secret123" in params

    def test_rejects_invalid_username(self, mock_session):
        request = CreateRoleRequest(username="bad; DROP TABLE", login=True, superuser=False)
        with pytest.raises(ValueError, match="invalid characters"):
            create_role(mock_session, request)


class TestAlterRole:
    def test_alter_password(self, mock_session):
        request = EditRoleRequest(password="newpass")
        result = alter_role(mock_session, "admin", request)
        assert "updated" in result
        executed_cql = mock_session.execute.call_args[0][0]
        assert "PASSWORD = %s" in executed_cql

    def test_no_changes(self, mock_session):
        request = EditRoleRequest()
        result = alter_role(mock_session, "admin", request)
        assert "No changes" in result


class TestDropRole:
    def test_drops_valid_role(self, mock_session):
        result = drop_role(mock_session, "old_role")
        assert "deleted" in result
        executed_cql = mock_session.execute.call_args[0][0]
        assert "DROP ROLE IF EXISTS" in executed_cql

    def test_rejects_invalid_role_name(self, mock_session):
        with pytest.raises(ValueError):
            drop_role(mock_session, "bad; DROP TABLE")


class TestListPermissions:
    def test_validates_role_name(self, mock_session):
        with pytest.raises(ValueError, match="invalid characters"):
            list_permissions(mock_session, "role'; DROP TABLE")

    def test_valid_role(self, mock_session):
        mock_row = MagicMock()
        mock_row.resource = "ALL KEYSPACES"
        mock_row.permission = "SELECT"
        mock_session.execute.return_value = [mock_row]

        result = list_permissions(mock_session, "admin")
        assert len(result) == 1
        assert result[0]["permission"] == "SELECT"


class TestGrantPermission:
    def test_grants_valid_permission(self, mock_session):
        result = grant_permission(mock_session, "SELECT", "ALL KEYSPACES", "viewer")
        assert "Granted" in result
        executed_cql = mock_session.execute.call_args[0][0]
        assert "GRANT SELECT ON ALL KEYSPACES TO" in executed_cql

    def test_rejects_invalid_permission(self, mock_session):
        with pytest.raises(ValueError, match="Invalid permission"):
            grant_permission(mock_session, "HACK; DROP TABLE", "ALL KEYSPACES", "viewer")

    def test_rejects_invalid_resource(self, mock_session):
        with pytest.raises(ValueError):
            grant_permission(mock_session, "SELECT", "INVALID; DROP", "viewer")

    def test_rejects_invalid_role(self, mock_session):
        with pytest.raises(ValueError, match="invalid characters"):
            grant_permission(mock_session, "SELECT", "ALL KEYSPACES", "bad; role")


class TestRevokePermission:
    def test_revokes_valid_permission(self, mock_session):
        result = revoke_permission(mock_session, "MODIFY", "KEYSPACE my_ks", "viewer")
        assert "Revoked" in result

    def test_rejects_invalid_permission(self, mock_session):
        with pytest.raises(ValueError, match="Invalid permission"):
            revoke_permission(mock_session, "INVALID", "ALL KEYSPACES", "viewer")
