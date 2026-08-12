from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from database import get_db
from config import settings
from models.user import User, UserStatus, UserRole, Project
from models.document import Document, DocumentStatus, ApprovalWorkflow
from models.audit_log import AuditLog
from models.dx_sync_metric import DxSyncMetric
from auth.dependencies import get_current_user
from services.access_control import can_access_all, visible_documents_query

router = APIRouter(prefix="/stats", tags=["Stats"])

# Audit log action names actually emitted by the backend (see api/auth.py).
# These are the real source of security event metrics surfaced on the console.
_LOGIN_SUCCESS_ACTIONS = ("m365_login_success",)
_LOGIN_FAILED_ACTIONS = (
    "m365_login_failed",
    "m365_user_not_found",
)
_PROVISION_ACTIONS = ("m365_user_provisioned",)


def _enum_value(v):
    """Return the plain string value for enum or string status/type keys."""
    return getattr(v, "value", v)


@router.get("/")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    visible_docs = visible_documents_query(db, current_user)
    total_documents = visible_docs.count() or 0
    visible_doc_ids = visible_docs.with_entities(Document.id).subquery()
    pending_approvals = (
        db.query(func.count(ApprovalWorkflow.id))
        .filter(ApprovalWorkflow.status == "pending")
        .join(Document, ApprovalWorkflow.document_id == Document.id)
        .filter(Document.id.in_(visible_doc_ids))
        .scalar()
        or 0
    )
    if can_access_all(current_user):
        active_users = (
            db.query(func.count(User.id))
            .filter(User.status == UserStatus.ACTIVE)
            .scalar()
            or 0
        )
    else:
        active_users = 0
    approved_this_month = (
        visible_docs.filter(
            Document.status == DocumentStatus.APPROVED,
            Document.updated_at >= thirty_days_ago,
        ).count()
        or 0
    )
    uploaded_this_week = (
        visible_docs.filter(Document.created_at >= seven_days_ago).count() or 0
    )
    total_file_size = (
        db.query(func.sum(Document.file_size))
        .filter(Document.id.in_(visible_doc_ids))
        .scalar()
        or 0
    )

    type_breakdown = (
        visible_docs.with_entities(Document.document_type, func.count(Document.id))
        .group_by(Document.document_type)
        .all()
    )
    status_breakdown = (
        visible_docs.with_entities(Document.status, func.count(Document.id))
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


@router.get(
    "/security",
    summary="セキュリティイベント統計（監査ログ実データ由来）",
    description=(
        "監査ログ（append-only ハッシュチェーン）に実際に記録された "
        "認証イベントを集計して返します。値は捏造ではなく audit_logs テーブルの実データです。"
    ),
)
def get_security_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregate real security events from the append-only audit log.

    All counts are derived from rows actually written to the audit_logs table
    (see api/auth.py). No synthetic/real-time values are fabricated.

    Admin-only: these metrics are derived from the audit log, whose direct
    access (api/audit_logs.list_audit_logs) is restricted to admins. Gating
    here keeps the aggregate view consistent and prevents non-admins from
    inferring audit data they cannot read directly.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    def _count(actions, since=None):
        q = db.query(func.count(AuditLog.id)).filter(AuditLog.action.in_(actions))
        if since is not None:
            q = q.filter(AuditLog.created_at >= since)
        return q.scalar() or 0

    total_events = db.query(func.count(AuditLog.id)).scalar() or 0
    active_sessions = (
        db.query(func.count(User.id)).filter(User.status == UserStatus.ACTIVE).scalar()
        or 0
    )

    return {
        # Real counts straight from the audit log.
        "total_events": total_events,
        "login_success_total": _count(_LOGIN_SUCCESS_ACTIONS),
        "login_failed_total": _count(_LOGIN_FAILED_ACTIONS),
        "login_failed_30d": _count(_LOGIN_FAILED_ACTIONS, since=thirty_days_ago),
        "provision_events_total": _count(_PROVISION_ACTIONS),
        # Active accounts (proxy for live sessions; same source as /stats active_users).
        "active_sessions": active_sessions,
    }


@router.get(
    "/security-config",
    summary="セキュリティ設定（実 config 由来・設定ベース）",
    description=(
        "バックエンドの実際の設定値（config.py / RBAC ロール定義）を返します。"
        "これはリアルタイムのトラフィック値ではなく、サーバが現在採用している設定そのものです。"
    ),
)
def get_security_config(
    current_user: User = Depends(get_current_user),
):
    """Return the server's actual security configuration.

    These are config-based (static) values reflecting the running config, not
    real-time traffic. Frontend must label them as such, never as live metrics.

    Admin-only: the security console is an administrative view; gating keeps it
    consistent with /stats/security and the admin-only audit log access.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return {
        # From config.py (real running settings).
        "access_token_expire_minutes": settings.access_token_expire_minutes,
        "refresh_token_expire_days": settings.refresh_token_expire_days,
        "jwt_algorithm": settings.algorithm,
        "max_file_size_mb": settings.max_file_size_mb,
        # From the RBAC role enum (real defined roles).
        "rbac_roles": [role.value for role in UserRole],
        # Audit log integrity is implemented (SHA-256 hash chain, append-only).
        "audit_chain_enabled": True,
        "audit_hash_algorithm": "SHA-256",
    }


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
    for project_id, status_val, count in rows:
        bucket = by_project.setdefault(
            project_id, {"total": 0, "ok": 0, "ng": 0, "warn": 0}
        )
        status_value = _enum_value(status_val)
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


@router.get(
    "/dx-sync",
    summary="DX 同期成功率（dx_sync_metrics 実データ由来）",
    description=(
        "CivilPDF-Editor の review-sidecar 送信（POST /documents/{id}/review-sidecar）の"
        "実測成功/失敗を集計します。値は dx_sync_metrics テーブルの実データです。"
        "SLO: 成功率 >= 99%。"
    ),
)
def get_dx_sync_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    rows = db.query(DxSyncMetric).all()
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    def _aware(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    rows = [r for r in rows if _aware(r.created_at) is not None]

    total = len(rows)
    success = sum(1 for r in rows if r.event_type == "success")
    error = total - success

    recent = [r for r in rows if _aware(r.created_at) >= thirty_days_ago]
    recent_total = len(recent)
    recent_success = sum(1 for r in recent if r.event_type == "success")
    recent_error = recent_total - recent_success

    by_error_kind: dict[str, int] = {}
    for r in recent:
        if r.event_type == "error" and r.error_kind:
            by_error_kind[r.error_kind] = by_error_kind.get(r.error_kind, 0) + 1

    # Last 6 calendar months (Python-side aggregation for SQLite/PostgreSQL parity).
    monthly: list[dict] = []
    for offset in range(5, -1, -1):
        month_start = (
            now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            - timedelta(days=offset * 31)
        ).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        bucket = [r for r in rows if month_start <= _aware(r.created_at) < month_end]
        monthly.append(
            {
                "month": month_start.strftime("%Y-%m"),
                "success": sum(1 for r in bucket if r.event_type == "success"),
                "error": sum(1 for r in bucket if r.event_type == "error"),
            }
        )

    def _rate(s, e):
        t = s + e
        return round(s / t * 100, 2) if t else None

    return {
        "total": total,
        "success": success,
        "error": error,
        "success_rate_total": _rate(success, error),
        "success_rate_30d": _rate(recent_success, recent_error),
        "recent_30d": {
            "total": recent_total,
            "success": recent_success,
            "error": recent_error,
        },
        "by_error_kind_30d": by_error_kind,
        "monthly": monthly,
    }
