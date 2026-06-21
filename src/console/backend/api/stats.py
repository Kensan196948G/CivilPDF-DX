from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone

from database import get_db
from models.user import User, UserStatus, Project
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
        db.query(func.count(User.id)).filter(User.status == UserStatus.ACTIVE).scalar()
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
        "by_type": {_enum_value(t): c for t, c in type_breakdown},
        "by_status": {_enum_value(s): c for s, c in status_breakdown},
    }


def _enum_value(v):
    """Return the plain string value for enum or string status/type keys."""
    return getattr(v, "value", v)


@router.get("/projects")
def get_project_stats(
    period: int = Query(30, ge=1, le=365, description="集計対象期間(日)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-project document statistics over the given period.

    Returns real document counts grouped by project, split into approved (ok),
    rejected (ng) and pending/draft (warn) buckets. No synthetic data.
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=period)

    # Authorization scope: admins see all projects; non-admins only the
    # projects they belong to (mirrors api/projects.list_projects), so per-project
    # aggregates cannot leak cross-organization data.
    if current_user.role.value == "admin":
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
    else:
        projects = sorted(
            current_user.projects, key=lambda p: p.created_at, reverse=True
        )
    project_ids = [p.id for p in projects]

    # One grouped query: (project_id, status) -> count, filtered by period and
    # restricted to the caller's visible projects.
    rows = (
        db.query(
            Document.project_id,
            Document.status,
            func.count(Document.id),
        )
        .filter(
            Document.created_at >= since,
            Document.project_id.in_(project_ids),
        )
        .group_by(Document.project_id, Document.status)
        .all()
    )

    # Aggregate counts per project.
    by_project: dict[str, dict[str, int]] = {}
    for project_id, status, count in rows:
        bucket = by_project.setdefault(
            project_id, {"total": 0, "ok": 0, "ng": 0, "warn": 0}
        )
        status_value = _enum_value(status)
        bucket["total"] += count
        if status_value == DocumentStatus.APPROVED.value:
            bucket["ok"] += count
        elif status_value == DocumentStatus.REJECTED.value:
            bucket["ng"] += count
        else:
            # draft / pending_review / archived -> treated as in-progress
            bucket["warn"] += count

    items = []
    for project in projects:
        bucket = by_project.get(project.id, {"total": 0, "ok": 0, "ng": 0, "warn": 0})
        items.append(
            {
                "id": project.id,
                "name": project.name,
                "code": project.code,
                "total": bucket["total"],
                "ok": bucket["ok"],
                "ng": bucket["ng"],
                "warn": bucket["warn"],
            }
        )

    return {"period": period, "items": items}


@router.get("/daily")
def get_daily_stats(
    period: int = Query(30, ge=1, le=365, description="集計対象期間(日)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daily document upload counts over the given period (oldest -> newest).

    Returns one entry per day so the dashboard trend chart reflects real
    upload activity instead of a pseudo-random series.
    """
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=period - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Authorization scope: non-admins only count documents in projects they
    # belong to, so the daily trend cannot leak cross-organization upload volume.
    docs_query = db.query(Document.created_at).filter(Document.created_at >= start)
    if current_user.role.value != "admin":
        member_ids = [p.id for p in current_user.projects]
        docs_query = docs_query.filter(Document.project_id.in_(member_ids))
    docs = docs_query.all()

    # Bucket by calendar day (UTC).
    counts: dict[str, int] = {}
    for (created_at,) in docs:
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        day_key = created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        counts[day_key] = counts.get(day_key, 0) + 1

    series = []
    for offset in range(period):
        day = (start + timedelta(days=offset)).strftime("%Y-%m-%d")
        series.append({"date": day, "count": counts.get(day, 0)})

    return {"period": period, "series": series}
