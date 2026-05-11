from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone

from database import get_db
from models.user import User, UserStatus
from models.document import Document, DocumentStatus, ApprovalWorkflow
from auth.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    total_documents = db.query(func.count(Document.id)).scalar() or 0
    pending_approvals = (
        db.query(func.count(ApprovalWorkflow.id))
        .filter(ApprovalWorkflow.status == "pending")
        .scalar()
        or 0
    )
    active_users = (
        db.query(func.count(User.id))
        .filter(User.status == UserStatus.ACTIVE)
        .scalar()
        or 0
    )
    approved_this_month = (
        db.query(func.count(Document.id))
        .filter(
            and_(
                Document.status == DocumentStatus.APPROVED,
                Document.updated_at >= thirty_days_ago,
            )
        )
        .scalar()
        or 0
    )
    uploaded_this_week = (
        db.query(func.count(Document.id))
        .filter(Document.created_at >= seven_days_ago)
        .scalar()
        or 0
    )
    total_file_size = db.query(func.sum(Document.file_size)).scalar() or 0

    type_breakdown = (
        db.query(Document.document_type, func.count(Document.id))
        .group_by(Document.document_type)
        .all()
    )
    status_breakdown = (
        db.query(Document.status, func.count(Document.id))
        .group_by(Document.status)
        .all()
    )

    return {
        "total_documents": total_documents,
        "pending_approvals": pending_approvals,
        "active_users": active_users,
        "approved_this_month": approved_this_month,
        "uploaded_this_week": uploaded_this_week,
        "total_file_size_bytes": total_file_size,
        "by_type": {t: c for t, c in type_breakdown},
        "by_status": {s: c for s, c in status_breakdown},
    }
