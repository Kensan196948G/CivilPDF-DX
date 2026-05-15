"""Physical deletion background job — GDPR Art.17 / 電子帳簿保存法.

Scans documents flagged with deletion_requested_at older than the grace period
and permanently removes the file from disk plus soft-deletes the DB record.
Audit logs are intentionally preserved (法的証跡保持義務).

Usage:
  Run via Celery: `celery -A services.deletion_job worker --loglevel=info`
  Or call `run_deletion_job(db)` directly from a scheduled endpoint / cron.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.document import Document
from services.audit_chain_service import create_chained_audit_log

logger = logging.getLogger(__name__)

DEFAULT_GRACE_DAYS = 30  # configurable; 30-day cooling-off period


def run_deletion_job(db: Session, grace_days: int = DEFAULT_GRACE_DAYS) -> dict:
    """Execute one pass of the physical deletion job.

    Args:
        db: SQLAlchemy session.
        grace_days: Minimum days after deletion_requested_at before physical deletion.

    Returns:
        dict with counts: processed, deleted_files, errors.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=grace_days)

    candidates = (
        db.query(Document)
        .filter(
            Document.deletion_requested_at != None,  # noqa: E711
            Document.deletion_requested_at <= cutoff,
        )
        .all()
    )

    deleted_files = 0
    errors = 0

    for doc in candidates:
        try:
            _physically_delete(db, doc)
            deleted_files += 1
        except Exception as exc:
            logger.error(
                "Failed to delete document %s: %s", doc.id, exc, exc_info=True
            )
            errors += 1

    logger.info(
        "Deletion job complete: processed=%d deleted=%d errors=%d grace_days=%d",
        len(candidates),
        deleted_files,
        errors,
        grace_days,
    )
    return {
        "processed": len(candidates),
        "deleted_files": deleted_files,
        "errors": errors,
        "grace_days": grace_days,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }


def _physically_delete(db: Session, doc: Document) -> None:
    """Remove file from disk and mark document as deleted in DB."""
    doc_id = doc.id
    file_path: Optional[str] = doc.file_path

    # Remove file from disk
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        logger.info("Deleted file from disk: %s", file_path)
    elif file_path:
        logger.warning("File not found on disk (already removed?): %s", file_path)

    # Null out personal data fields — retain record skeleton for audit linkage
    doc.file_path = None  # type: ignore[assignment]
    doc.ocr_text = None
    doc.extra_data = {}
    doc.is_archived = True
    doc.archived_at = datetime.now(timezone.utc)

    db.commit()

    # Immutable audit trail entry (not deleted even after GDPR erasure)
    create_chained_audit_log(
        db,
        user_id=None,  # system job, no user actor
        action="gdpr_physical_deletion",
        resource_type="document",
        resource_id=doc_id,
        detail="physical deletion executed after grace period; file_path nulled",
        ip_address=None,
    )
    logger.info("Physical deletion complete for document %s", doc_id)
