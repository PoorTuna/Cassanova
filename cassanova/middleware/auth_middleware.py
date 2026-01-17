from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from cassanova.api.dependencies.auth import get_current_user

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            user = await get_current_user(request)
            request.state.user = user
        except Exception:
            request.state.user = None
            
        response = await call_next(request)
        return response
