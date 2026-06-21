from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone

from database import get_db
from config import settings
from models.user import User, UserStatus, UserRole
from models.document import Document, DocumentStatus, ApprovalWorkflow
from models.audit_log import AuditLog
from auth.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])

# Audit log action names actually emitted by the backend (see api/auth.py).
# These are the real source of security event metrics surfaced on the console.
_LOGIN_SUCCESS_ACTIONS = ("m365_login_success",)
_LOGIN_FAILED_ACTIONS = (
    "m365_login_failed",
    "m365_user_not_found",
)
_PROVISION_ACTIONS = ("m365_user_provisioned",)


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
        "by_type": {t: c for t, c in type_breakdown},
        "by_status": {s: c for s, c in status_breakdown},
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
    """
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
    """
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
