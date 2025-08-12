# Cassanova

**Cassanova** is a web-based Cassandra compatible monitoring and operations tool.  
Built with Python using the FastAPI framework, 
it aims to provide real-time cluster introspection, 
interactive CQL tools and diagnostic utilities.

[![Docker Pulls](https://img.shields.io/docker/pulls/poortuna/cassanova.svg)](https://hub.docker.com/r/poortuna/cassanova)
---

## ✨ Features

- Cluster Topology Graph Visualization
- Keyspace & Schema Exploration and Graph Visualization
- Interactive CQL Terminal with History
- Basic Table Operations
- Nodetool Status Visualization
- Diagnostic Tools (sstabledump, cassandra-stress, nodetool, etc.)
- Read-Only Settings Page 
---

## 🐳 Docker Installation

To run Cassanova using Docker:

#### 1. Pull the image:

```bash
docker pull poortuna/cassanova:v1.0.4
```

#### 2. Create a configuration file:

Create a `cassanova.json` configuration file. Example:

```json
{
  "app_config": {
    "host": "0.0.0.0",
    "port": 8080,
    "routers": ["cassanova_ui_router", "cassanova_api_router"]
  },
  "monitoring_url": "https://localhost:8080",
  "clusters": {
    "orencluster": {
      "contact_points": [
        "localhost"
      ]
    }
  }
}
```

Save this as `cassanova.json` in your current directory.

#### 3. Run Cassanova:

```bash
docker run -p 8080:8080   -e CASSANOVA_CONFIG_PATH=/config/cassanova.json   -v $(pwd)/cassanova.json:/config/cassanova.json   poortuna/cassanova:v1.0.4
```

> Make sure Cassandra is accessible from within the container, and your `contact_points` in the config file point to a resolvable address (e.g., `host.docker.internal` on macOS/Windows).

#### 4. Access the UI:

Open [http://localhost:8080](http://localhost:8080) in your browser.


---

## ⚙️ Configuration

Cassanova is configured using a single JSON file and a required environment variable:

- `CASSANOVA_CONFIG_PATH` must point to a valid JSON config file

Please check the reference json configuration file for further details.

---

## 📁 Configuration Loading Logic

Cassanova uses a Pydantic-powered configuration system and requires a valid path to your config file.  
This is injected via:

```bash
export CASSANOVA_CONFIG_PATH=/path/to/cassanova.json
```

Environment variable support and `.env` files will be added in the future.

---

## 🛠️ Development

To run locally:

- Please Note that you should run Cassanova in a unix based environment
  or some features (like the tools page) won't function properly

```bash
git clone https://github.com/poortuna/cassanova
cd cassanova
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export CASSANOVA_CONFIG_PATH=./cassanova.json
python -m cassanova.run
```

Feel free to improve/suggest new features!

---

## 📄 License

Cassanova is open source, licensed under the MIT License.
