from fastapi import FastAPI
from uvicorn import run

from cassanova.api.bootstrap import bootstrap_app
from cassanova.api.server_config import build_uvicorn_config
from cassanova.config.cassanova_config import get_clusters_config

config = get_clusters_config()
app_config = config.app_config

app = FastAPI()
bootstrap_app(app, app_config)

if __name__ == "__main__":
    uvicorn_config = build_uvicorn_config(app, app_config)
    run(**uvicorn_config)
