from http import HTTPStatus

from cassandra.cluster import NoHostAvailable
from fastapi import FastAPI
from fastapi.requests import Request
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")


def add_cluster_unavailable_exceptions(app: FastAPI):
    @app.exception_handler(NoHostAvailable)
    async def cluster_unavailable_exception_handler(request: Request, exc: NoHostAvailable):
        return templates.TemplateResponse("exceptions/cluster-down.html", {"request": request},
                                          status_code=HTTPStatus.SERVICE_UNAVAILABLE)
