from fastapi import Request, FastAPI
from fastapi.responses import RedirectResponse
from cassanova.exceptions.auth_exceptions import LoginRequired

async def auth_exception_handler(request: Request, exc: LoginRequired):
    return RedirectResponse(url="/login?next=" + request.url.path, status_code=303)

def add_auth_exception_handler(app: FastAPI):
    app.add_exception_handler(LoginRequired, auth_exception_handler)
