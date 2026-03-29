from logging import getLogger

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

logger = getLogger(__name__)


def add_default_exceptions(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        return JSONResponse({"error": "Internal server error"}, status_code=500)
