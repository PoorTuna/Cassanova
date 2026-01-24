# Cassanova

**Cassanova** is a modern, stateless, web-based operations hub for Apache Cassandra.  
Built with Python (FastAPI), it provides real-time cluster introspection, powerful data exploration tools, and a secure, role-based management interface.

[![Docker Pulls](https://img.shields.io/docker/pulls/poortuna/cassanova.svg)](https://hub.docker.com/r/poortuna/cassanova)

---

## ✨ Features

### 🔐 Security & RBAC
- **Stateless Authentication**: Fully configuration-driven JWT authentication. No database required.
- **Granular Permissions**: Define roles with specific permissions (e.g., `cluster:view`, `tools:cqlsh`, `data:write`).
- **Secure Access**: Protected API endpoints and role-aware UI elements (Sidebar, Dashboards).
- **Audit Ready**: Centralized login flow with secure session handling.

### 📊 Advanced Data Explorer
- **Smart Filtering**: Filter data by Partition Keys, Clustering Keys, or specific columns with an intuitive UI.
- **Cross-View Integration**: Filters persist across Data Layout graphs and List views.
- **Data Management**: Insert new rows directly via a schema-aware form.
- **Topology Visualization**: Interactive `vis.js` graphs showing Token Ring and Schema relationships.

### 🛠️ Operational Tools
- **Keyspace & Table Builders**: specialized UI for creating and modifying Keyspaces and Tables visually.
- **Interactive CQL Console**: A rich web-based terminal with history, syntax highlighting, and auto-complete.
- **Query Trace Visualization**: A visualized list for analyzing query performance and latency.
- **Process Management**: Web interfaces for `sstabledump`, `nodetool`, and `cassandra-stress`.

### ⚡ Core Capabilities
- **Cluster Introspection**: Real-time Node status, VNode distribution, and Token Range maps.
- **Multi-Cluster Support**: Manage multiple Cassandra clusters from a single dashboard.
- **Theme Support**: Includes Dark, Light, and custom themes (Orokin, Kibana, etc.).

---

## 🐳 Docker Installation

To run Cassanova using Docker:

#### 1. Pull the image:

```bash
docker pull poortuna/cassanova:v1.4.0
```

#### 2. Create a configuration file:

Create a `cassanova.json` file. This now includes the new **Auth** section:

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
    "suffix": "-service"
  }
}
```

#### 3. Run Cassanova:

```bash
docker run -p 8080:8080 \
  -e CASSANOVA_CONFIG_PATH=/config/cassanova.json \
  -v $(pwd)/cassanova.json:/config/cassanova.json \
  poortuna/cassanova:v1.4.0
```

> **Note**: Ensure your Cassandra nodes are reachable from within the container.

#### 4. Access the UI:

Open [http://localhost:8080](http://localhost:8080). Log in with the credentials defined in your JSON config.

---

## ⚙️ Configuration

Cassanova is entirely config-driven via `CASSANOVA_CONFIG_PATH`.
The configuration supports hot-reloading for most UI settings, though Auth changes currently require a restart.

### 🐙 Kubernetes Service Discovery (K8ssandra)

Cassanova can automatically discover `K8ssandraCluster` instances from a Kubernetes cluster.

| Setting | Description | Default |
|---------|-------------|---------|
| `k8s.enabled` | Enable K8s discovery on startup | `false` |
| `k8s.kubeconfig` | Path to kubeconfig file | `null` |
| `k8s.namespace` | Namespace to scan (or all if null) | `null` |
| `k8s.suffix` | Service name suffix (e.g., `-metallb`) | `-service` |

**How it works:**
1. On startup, if `k8s.enabled` is `true`, Cassanova scans for `K8ssandraCluster` CRs.
2. For each cluster, it fetches credentials from the `<cluster>-superuser` Secret.
3. It finds Services matching `<cluster>-<dc><suffix>` and extracts contact points (LoadBalancer IP, ExternalIP, or ClusterIP).
4. Discovered clusters are merged into the `clusters` config.

**Example (Environment Variables):**
```bash
export CASSANOVA_K8S__ENABLED=true
export CASSANOVA_K8S__KUBECONFIG=/path/to/kubeconfig
export CASSANOVA_K8S__SUFFIX=-metallb
```

### 🚑 Automated Remediation

Cassanova includes a **Remediation Dashboard** to handle Cassandra node failures in Kubernetes (e.g., OpenShift with LVMS).

| Setting | Description | Default |
|---------|-------------|---------|
| `remediation.enabled` | Enable the remediation service | `false` |
| `remediation.poll_interval_seconds` | How often to check for failures | `30` |
| `remediation.max_concurrent_per_dc` | Max simultaneous recoveries per DC | `1` |
| `remediation.max_concurrent_per_rack` | Max simultaneous recoveries per Rack | `1` |
| `remediation.auto_poll_enabled` | Automatically poll pending pods (disable for manual-only) | `true` |

**Recovery Workflow:**
1. **Detect**: Periodically checks for `Pending` pods managed by K8ssandra that are unschedulable due to **Volume Node Affinity** (indicative of a lost local volume/node).
2. **Review**: Administrator sees these pods in the **Remediation Dashboard** and clicks "Approve".
3. **Recover**:
   - Removes finalizers from PVCs and Pod to allow deletion.
   - Triggers a `K8ssandraTask` (`replacenode`) to bootstrap a fresh pod on a new node.
   - Monitors the replacement until completion.

**Enable via Config:**
```json
"remediation": {
  "enabled": true,
  "poll_interval_seconds": 30,
  "auto_poll_enabled": true
}
```

---

## 🛠️ Development

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

## 📄 License

Cassanova is open source, licensed under the MIT License.
