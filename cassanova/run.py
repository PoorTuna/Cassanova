from fastapi import FastAPI
from uvicorn import run

from cassanova.bootstrap import bootstrap_app
from cassanova.config.cassanova_config import get_clusters_config

app = FastAPI()

if __name__ == '__main__':
    app_config = get_clusters_config().app_config
    bootstrap_app(app, app_config)
    run(app, host=app_config.host, port=app_config.port)
