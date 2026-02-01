# Cassanova

**Cassanova** is a web-based management interface for Apache Cassandra.
Built with Python (FastAPI), it provides cluster monitoring, data exploration, and configuration-driven role-based access control.

[![Docker Pulls](https://img.shields.io/docker/pulls/poortuna/cassanova.svg)](https://hub.docker.com/r/poortuna/cassanova)

---

## Features

### Security & RBAC
- **Stateless Authentication**: Configuration-driven JWT authentication requiring no database.
- **Granular Permissions**: Role definitions with specific permissions (e.g., `cluster:view`, `tools:cqlsh`, `data:write`).
- **Access Control**: Protected API endpoints and role-aware UI elements.
- **Auditing**: Centralized login flow with secure session handling.

### Data Explorer
- **Filtering**: Filter data by Partition Keys, Clustering Keys, or specific columns.
- **Cross-View Integration**: Filters persist across Data Layout graphs and List views.
- **Data Management**: Form-based row insertion, aware of table schema.
- **Topology Visualization**: Graphs showing Token Ring and Schema relationships.

### Operational Tools
- **Schema Management**: UI for creating and modifying Keyspaces and Tables.
- **CQL Console**: Web-based terminal with history and syntax highlighting.
- **Query Tracing**: List view for analyzing query performance and latency.
- **Process Management**: Web interfaces for `sstabledump`, `nodetool`, and `cassandra-stress`.

### Core Capabilities
- **Cluster Monitoring**: Node status, VNode distribution, and Token Range maps.
- **Multi-Cluster Support**: Manage multiple Cassandra clusters from a single dashboard.
- **Theming**: Includes Dark and Light themes.

---

## Docker Installation

To run Cassanova using Docker:

#### 1. Pull the image:

```bash
docker pull poortuna/cassanova:v1.6.1
```

#### 2. Create a configuration file:

Create a `cassanova.json` file. This includes the `auth` section:

```json
{
  "app_config": {
    "host": "0.0.0.0",
    "port": 8080,
    "routers": ["cassanova_ui_router", "cassanova_api_router"]
  },
  "auth": {
    "enabled": true,
    "secret_key": "CHANGE_THIS_SECRET_KEY",
    "algorithm": "HS256",
    "session_expire_minutes": 120,
    "users": [
      {
        "username": "admin",
        "password": "admin_password",
        "roles": ["admin"]
      },
      {
        "username": "viewer",
        "password": "view_only_password",
        "roles": ["viewer"]
      }
    ],
    "roles": [
      { "name": "admin", "permissions": ["*"] },
      { "name": "viewer", "permissions": ["cluster:view", "users:view"] }
    ]
  },
  "clusters": {
    "proda": {
      "contact_points": ["10.0.0.1", "10.0.0.2"],
      "port": 9042
    }
  },
  "k8s": {
    "enabled": true,
    "kubeconfig": "/etc/cassanova/kubeconfig",
    "namespace": "default",
    "suffix": "-service",
    "periodic_discovery_enabled": true,
    "discovery_interval_seconds": 60
  }
}
```

> **Optional:** Enable TLS by adding `"tls": {"enabled": true, "cert_file": "/path/to/cert.crt", "key_file": "/path/to/key.key"}` under `app_config`.

#### 3. Run Cassanova:

```bash
docker run -p 8080:8080 \
  -e CASSANOVA_CONFIG_PATH=/config/cassanova.json \
  -v $(pwd)/cassanova.json:/config/cassanova.json \
  poortuna/cassanova:v1.6.1
```

> **Note**: Ensure your Cassandra nodes are reachable from within the container.

#### 4. Access the UI:

Open [http://localhost:8080](http://localhost:8080). Log in with the credentials defined in your JSON config.

---

## Configuration

Cassanova is configured via `CASSANOVA_CONFIG_PATH`.
Most UI settings support hot-reloading. Auth changes require a restart.

### Kubernetes Service Discovery (K8ssandra)

Cassanova can discover `K8ssandraCluster` instances from a Kubernetes cluster.

| Setting | Description | Default |
|---------|-------------|---------|
| `k8s.enabled` | Enable K8s discovery on startup | `false` |
| `k8s.kubeconfig` | Path to kubeconfig file | `null` |
| `k8s.namespace` | Namespace to scan (or all if null) | `null` |
| `k8s.suffix` | Service name suffix (e.g., `-metallb`) | `-service` |
| `k8s.periodic_discovery_enabled` | Enable periodic background scans | `false` |
| `k8s.discovery_interval_seconds` | Interval for periodic scans in seconds | `60` |

**Mechanism:**
1. Cassanova scans for `K8ssandraCluster` CRs.
2. Fetches credentials from the `<cluster>-superuser` Secret.
3. Identifies Services matching `<cluster>-<dc><suffix>` to extract contact points.
4. Merges discovered clusters into the configuration.

### Node Recovery

Includes a dashboard to handle Cassandra node failures in Kubernetes (e.g., OpenShift with LVMS).

| Setting | Description | Default |
|---------|-------------|---------|
| `k8s.node_recovery.enabled` | Enable the node recovery service | `false` |

**Recovery Workflow:**
1. **Detect**: Queries for `Pending` pods with **Volume Node Affinity** issues.
2. **Review**: Administrator approves the recovery.
3. **Recover**: Creates a `K8ssandraTask` (`replacenode`) to fix the pod.

### TLS/HTTPS Support

Supports TLS encryption.

| Setting | Description | Default |
|---------|-------------|---------|
| `app_config.tls.enabled` | Enable HTTPS/TLS | `false` |
| `app_config.tls.cert_file` | Path to SSL certificate (.crt/.pem) | Required if enabled |
| `app_config.tls.key_file` | Path to private key (.key/.pem) | Required if enabled |
| `app_config.tls.ca_bundle` | Optional CA certificate chain | `null` |
| `app_config.tls.min_tls_version` | Minimum TLS version (`TLSv1_2` or `TLSv1_3`) | `TLSv1_2` |
| `app_config.tls.enforce_https` | Redirect HTTP → HTTPS (301) | `true` |
| `app_config.tls.hsts_enabled` | Enable HSTS security headers | `true` |
| `app_config.tls.hsts_max_age` | HSTS max-age in seconds | `31536000` (1 year) |
| `app_config.tls.hsts_include_subdomains` | Apply HSTS to subdomains | `false` |

**Security Features:**
- **Cipher Suites** - ECDHE/CHACHA20/AES-GCM ciphers
- **Protocols** - TLS 1.2+ enforcement
- **HSTS** - Prevents downgrade attacks
- **Secure Cookies** - Session cookies marked `Secure` and `SameSite=Lax`
- **Redirects** - Forces HTTPS connections

### LDAP Integration

Supports LDAP/AD integration for centralized user management.

| Setting | Description | Default |
|---------|-------------|---------|
| `auth.ldap.enabled` | Enable LDAP auth | `false` |
| `auth.ldap.server_uri` | LDAP URI (ldap:// or ldaps://) | `ldap://localhost:389` |
| `auth.ldap.base_dn` | Base DN for user/group search | `dc=example,dc=com` |
| `auth.ldap.bind_dn` | Service account DN (null for anonymous) | `null` |
| `auth.ldap.role_mapping` | Map LDAP groups to Cassanova roles | `{}` |

**Role Mapping Strategies:**
1. **Group Name**: Matches the `cn` (or configured attribute) of the group. e.g., `"Domain Admins": ["admin"]`.
2. **Exact DN**: Matches the full Distinguished Name of the group. e.g., `"cn=group,dc=com": ["admin"]`.
3. **Branch/Suffix**: Matches any group located under a specific OU. e.g., `"ou=Admins,dc=com": ["admin"]`.

**Example Config:**
```json
"auth": {
  "enabled": true,
  "ldap": {
    "enabled": true,
    "server_uri": "ldaps://ad.example.com:636",
    "bind_dn": "cn=svc-cassanova,ou=Users,dc=example,dc=com",
    "bind_password": "secret_password",
    "base_dn": "dc=example,dc=com",
    "user_search_filter": "(sAMAccountName={username})",
    "group_search_base": "ou=Groups,dc=example,dc=com",
    "group_search_filter": "(member={user_dn})",
    "role_mapping": {
      "Domain Admins": ["admin"],
      "Developers": ["viewer"],
      "cn=SpecificGroup,ou=Groups,dc=example,dc=com": ["admin"],
      "ou=NuclearBranch,dc=example,dc=com": ["admin"]
    }
  }
}
```

---

## Development

To run locally (Linux/WSL recommended):

```bash
git clone https://github.com/poortuna/cassanova
cd cassanova
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set config path
export CASSANOVA_CONFIG_PATH=./config/dev_config.json

# Run Server
python -m cassanova.run
```

---

## License

Cassanova is open source, licensed under the MIT License.
