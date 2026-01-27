from http import HTTPStatus

from fastapi import FastAPI, Request
from starlette.templating import Jinja2Templates

from cassanova.exceptions.system_views_unavailable import SystemViewsUnavailableException

templates = Jinja2Templates(directory="web/templates")


def add_system_views_unavailable_exception_handler(app: FastAPI):
    @app.exception_handler(SystemViewsUnavailableException)
    async def system_views_unavailable_handler(request: Request, exc: SystemViewsUnavailableException):
        return templates.TemplateResponse("exceptions/system-views-unavailable.html", {
            "request": request,
            "error_message": exc.message
        }, status_code=HTTPStatus.OK)
