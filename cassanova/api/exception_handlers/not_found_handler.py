from http import HTTPStatus

from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from fastapi.requests import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from cassanova.web.template_config import templates


def add_notfound_exceptions(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def not_found_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        if exc.status_code == 404:
            return templates.TemplateResponse(
                "exceptions/404.html", {"request": request}, status_code=HTTPStatus.NOT_FOUND
            )
        return await http_exception_handler(request, exc)
