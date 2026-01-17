# Security & RBAC Configuration

Cassanova v1.4.0 introduces a stateless, configuration-driven Role-Based Access Control (RBAC) system. This document outlines how to configure users, roles, and permissions in your `cassanova.json` file.

## ⚙️ Configuration Structure

The security configuration lives under the `auth` key in your main configuration JSON.

```json
"auth": {
  "enabled": true,
  "secret_key": "YOUR_SECRET_KEY",
  "users": [...],
  "roles": [...]
}
```

### Key Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `enabled` | `bool` | Set to `true` to enforce login and permissions. If `false`, the system runs in "Anonymous Admin" mode. |
| `secret_key` | `string` | A strong random string used to sign session cookies (JWTs). **Change this in production!** |
| `session_expire_minutes` | `int` | Session duration in minutes (Default: 120). |
| `algorithm` | `string` | Hashing algorithm (Default: `HS256`). |

---

## 👥 Users & Roles

You can define as many users and roles as needed.

### Defining Roles

Roles are simply collections of permissions.

```json
{
  "name": "viewer",
  "permissions": ["cluster:view", "tools:view"]
}
```

### Defining Users

Users are assigned one or more roles.

```json
{
  "username": "alice",
  "password": "alice_password",
  "roles": ["viewer", "operator"]
}
```

> **Note**: Passwords in the config can be provided as plain text (automatically hashed on load) or as pre-hashed bcrypt strings (starting with `$2a$` or `$2b$`) for enhanced security.

---

## 🛡️ Available Permissions

The following permissions control access to specific parts of the Cassanova interface:

| Permission | Description | Access Grants |
| :--- | :--- | :--- |
| **`cluster:view`** | Basic Read Access | Cluster Overview, Nodes List, VNodes Visualizer. |
| **`tools:view`** | Operational Tools | Access to the Tools Hub (SSTableDump, Stress, etc.). |
| **`tools:cqlsh`** | CQL Console | Access to the interactive CQLSh web terminal. |
| **`users:view`** | User Management | Access to the Users management page. |
| **`settings:view`** | Configuration | Access to the Read-Only Settings page. |
| **`*`** | Superuser | Grants **ALL** permissions automatically. |

### Wildcards

The system supports basic wildcards:
- `*` grants everything.
- `tools:*` would grant both `tools:view` and `tools:cqlsh`.

---

## 📝 Example Configuration

A complete example of a secure setup:

```json
{
  "auth": {
    "enabled": true,
    "secret_key": "super_secret_key_123",
    "users": [
      {
        "username": "admin",
        "password": "ChangeMe!",
        "roles": ["admin"]
      },
      {
        "username": "dev",
        "password": "dev",
        "roles": ["developer"]
      }
    ],
    "roles": [
      {
        "name": "admin",
        "permissions": ["*"]
      },
      {
        "name": "developer",
        "permissions": ["cluster:view", "tools:cqlsh", "tools:view"]
      }
    ]
  }
}
```
