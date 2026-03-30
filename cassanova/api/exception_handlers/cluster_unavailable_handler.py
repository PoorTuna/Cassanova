from http import HTTPStatus

from cassandra import UnresolvableContactPoints
from cassandra.cluster import NoHostAvailable
from fastapi import FastAPI
from fastapi.requests import Request
from starlette.responses import Response

from cassanova.web.template_config import templates


def add_cluster_unavailable_exceptions(app: FastAPI) -> None:
    @app.exception_handler(NoHostAvailable)
    async def cluster_unavailable_exception_handler(
        request: Request, exc: NoHostAvailable
    ) -> Response:
        return templates.TemplateResponse(
            "exceptions/cluster-down.html",
            {"request": request, "exception": str(exc)},
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )

    @app.exception_handler(UnresolvableContactPoints)
    async def unresolvable_contact_points_handler(
        request: Request, exc: UnresolvableContactPoints
    ) -> Response:
        return templates.TemplateResponse(
            "exceptions/cluster-down.html",
            {
                "request": request,
                "exception": (
                    "Could not resolve any contact points."
                    " Please check your cluster configuration connectivity."
                ),
            },
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )
