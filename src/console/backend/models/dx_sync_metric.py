from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
import uuid

from database import Base


class DxSyncMetric(Base):
    """Server-side DX sync outcome metric (CivilPDF-Editor -> console).

    Records one row per POST /api/v1/documents/{id}/review-sidecar request
    so the monthly success rate can be aggregated without parsing HTTP logs.
    The Editor client itself does not send telemetry; this table is the
    authoritative source for the DX sync SLI (target >= 99%).
    """

    __tablename__ = "dx_sync_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    document_id = Column(String, nullable=True)
    event_type = Column(String, nullable=False, index=True)  # success | error
    status_code = Column(Integer, nullable=False)
    error_kind = Column(
        String, nullable=True
    )  # auth|rbac|not_found|too_large|invalid|server|network
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
