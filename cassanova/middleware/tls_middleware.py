from fastapi import Request, status
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next):
        if request.url.scheme == "http":
            url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(url), status_code=status.HTTP_301_MOVED_PERMANENTLY)
        
        response = await call_next(request)
        return response


class HSTSMiddleware(BaseHTTPMiddleware):
    
    def __init__(self, app: ASGIApp, max_age: int = 31536000, include_subdomains: bool = False):
        super().__init__(app)
        self.max_age = max_age
        self.include_subdomains = include_subdomains
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        hsts_value = f"max-age={self.max_age}"
        if self.include_subdomains:
            hsts_value += "; includeSubDomains"
        
        response.headers["Strict-Transport-Security"] = hsts_value
        return response


class SecureCookieMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if "set-cookie" in response.headers:
            cookies = response.headers.get_list("set-cookie")
            response.headers.pop("set-cookie")
            
            for cookie in cookies:
                if "Secure" not in cookie:
                    cookie += "; Secure"
                if "SameSite" not in cookie:
                    cookie += "; SameSite=Lax"
                response.headers.append("set-cookie", cookie)
        
        return response
