from http import HTTPStatus

from fastapi import FastAPI, Request
from starlette.responses import Response

from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException
from cassanova.web.template_config import templates


def add_system_views_unavailable_exception_handler(app: FastAPI) -> None:
    @app.exception_handler(SystemViewsUnavailableException)
    async def system_views_unavailable_handler(
        request: Request, exc: SystemViewsUnavailableException
    ) -> Response:
        return templates.TemplateResponse(
            "exceptions/system-views-unavailable.html",
            {"request": request, "error_message": exc.message},
            status_code=HTTPStatus.OK,
        )
