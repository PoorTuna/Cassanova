from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from cassanova.api.dependencies.auth import get_current_user


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            user = await get_current_user(request)
            request.state.user = user
        except Exception:
            request.state.user = None

        response = await call_next(request)
        return response
