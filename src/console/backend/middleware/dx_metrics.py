"""DX sync metrics middleware — records review-sidecar API outcomes."""

import logging
import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from database import get_db
from models.dx_sync_metric import DxSyncMetric

logger = logging.getLogger("dx_metrics")

_SIDECAR_PATH_RE = re.compile(r"^/api/v1/documents/[^/]+/review-sidecar$")


def _error_kind(status_code: int) -> str:
    if status_code == 401:
        return "auth"
    if status_code == 403:
        return "rbac"
    if status_code == 404:
        return "not_found"
    if status_code == 413:
        return "too_large"
    if status_code in (400, 422):
        return "invalid"
    if status_code >= 500:
        return "server"
    return "other"


class DxSyncMetricsMiddleware(BaseHTTPMiddleware):
    """Best-effort metric recording; never fails or slows the API response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method != "POST" or not _SIDECAR_PATH_RE.match(request.url.path):
            return await call_next(request)

        response = await call_next(request)
        user_id = getattr(request.state, "user_id", None)
        status = response.status_code
        try:
            # Resolve through the app's dependency_overrides so tests share the
            # same DB session factory as the API routes.
            resolver = request.app.dependency_overrides.get(get_db, get_db)
            db_gen = resolver()
            db = next(db_gen)
            try:
                db.add(
                    DxSyncMetric(
                        user_id=user_id,
                        document_id=request.path_params.get("doc_id"),
                        event_type="success" if 200 <= status < 300 else "error",
                        status_code=status,
                        error_kind=None if 200 <= status < 300 else _error_kind(status),
                    )
                )
                db.commit()
            finally:
                try:
                    next(db_gen)
                except StopIteration:
                    pass
                db_gen.close()
        except Exception:  # noqa: BLE001 - metric must never break the API
            logger.exception("failed to record DX sync metric")
        return response
