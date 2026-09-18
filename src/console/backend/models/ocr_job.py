"""OCR / text-extraction job model.

Jobs used to live in a module-level dict (`_jobs`), so they were invisible to any
other worker process and vanished on restart. `docker-compose.prod.yml` runs
`uvicorn ... --workers ${UVICORN_WORKERS:-4}` (2 in `.env`), which meant
`GET /ocr/jobs/{job_id}` returned 404 roughly half the time depending on which
worker served the poll. Persisting the job makes it shared and durable.

`status` is a plain String on purpose: PostgreSQL enum labels cannot be removed
and the model/migration drift they allow already caused a production defect
(see migration n4o5p6q7r8s9), so a small, validated string set is used instead.
"""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base

# Attempted values for `status`. Kept out of the database (see module docstring).
OCR_STATUS_COMPLETED = "completed"
OCR_STATUS_UNSUPPORTED = "unsupported"
OCR_STATUS_FAILED = "failed"

# Engine identifier reported to clients. The console performs *text-layer
# extraction*, not OCR: no OCR engine (tesseract/easyocr/cloud OCR) is a
# dependency, so an image-only PDF cannot be recognised.
OCR_ENGINE_TEXT_LAYER = "pypdf-text-layer"


class OcrJob(Base):
    __tablename__ = "ocr_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    # Who asked for the extraction. Access is still decided by the document's
    # visibility (see api/ocr.py) so it follows the existing RBAC model.
    requested_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    status = Column(String, nullable=False)
    engine = Column(String, nullable=False)
    language = Column(String, nullable=False, default="jpn")
    enable_vertical = Column(Boolean, nullable=False, default=True)

    page_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    # [{page: int, text: str}] — extracted text layer, never a placeholder.
    pages = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document")
    requester = relationship("User")
