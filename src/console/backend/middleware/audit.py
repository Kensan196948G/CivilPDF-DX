"""Audit logging middleware — records every mutating API request."""

import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("audit")

SKIP_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc"}
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _extract_user_id(request: Request) -> str | None:
    """Best-effort user id from the Bearer token (no DB lookup)."""
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        from auth.jwt import decode_token

        payload = decode_token(token)
        return payload.get("sub")
    except HTTPException:
        # Invalid/expired token: leave user_id None, request is recorded anyway.
        return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in AUDIT_METHODS or request.url.path in SKIP_PATHS:
            return await call_next(request)

        request.state.user_id = _extract_user_id(request)
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id = getattr(request.state, "user_id", None)
        logger.info(
            json.dumps(
                {
                    "event": "api_call",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                    "ip": request.client.host if request.client else None,
                },
                ensure_ascii=False,
            )
        )
        return response
