from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")


def add_default_exceptions(app: FastAPI):
    @app.exception_handler(Exception)
    async def default_exception_handler(request: Request, exc: Exception):
        return JSONResponse({"error": str(exc)}, status_code=500)
