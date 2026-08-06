"""Security headers middleware.

Adds a baseline of browser security headers to every response. The public
deployment terminates TLS at Cloudflare, so HSTS is only emitted when the
request is already HTTPS (direct HTTPS or via X-Forwarded-Proto).
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_DOC_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _DOC_PATHS:
            # FastAPI docs load Swagger UI assets from a CDN; a strict
            # script-src 'self' CSP would break them.
            return await call_next(request)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        if request.url.scheme == "https" or forwarded_proto == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
