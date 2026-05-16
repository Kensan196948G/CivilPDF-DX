"""Privacy management API — GDPR Art.17 (right to erasure) and CCPA compliance."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.consent import ConsentRecord, ConsentType
from models.document import Document
from models.user import User, UserRole
from services.audit_chain_service import create_chained_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["Privacy & Compliance"])


# ---------- GDPR/CCPA Data Deletion ----------

class DeletionRequestResponse(BaseModel):
    user_id: str
    documents_marked: int
    deletion_requested_at: str
    audit_log_id: str


@router.delete(
    "/users/{user_id}/data",
    response_model=DeletionRequestResponse,
    summary="GDPR/CCPA データ削除権 (Right to Erasure)",
    description=(
        "ユーザー自身または管理者が全文書に削除フラグを立てます（論理削除）。"
        "物理削除はバックグラウンドジョブが `archive_grace_days` 経過後に実行します。"
        "監査ログへの記録は削除されません（法的証跡保持義務）。"
    ),
)
def request_data_deletion(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # GDPR Art.17: users may request erasure of their own data; admins may act for any user
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    now = datetime.now(timezone.utc)
    docs = db.query(Document).filter(
        Document.owner_id == user_id,
        Document.deletion_requested_at == None,  # noqa: E711
    ).all()

    for doc in docs:
        doc.deletion_requested_at = now

    db.commit()

    # Audit log must survive even after data deletion (法的証跡保持)
    audit = create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="gdpr_deletion_request",
        resource_type="user",
        resource_id=user_id,
        detail=json.dumps({
            "target_user_id": user_id,
            "target_email": target_user.email,
            "documents_marked": len(docs),
            "requester_id": current_user.id,
        }, ensure_ascii=False),
        ip_address=None,
    )

    logger.info(
        "GDPR deletion request: user=%s target=%s docs=%d",
        current_user.id, user_id, len(docs),
    )
    return DeletionRequestResponse(
        user_id=user_id,
        documents_marked=len(docs),
        deletion_requested_at=now.isoformat(),
        audit_log_id=audit.id,
    )


# ---------- GDPR/CCPA Data Portability ----------

class DataExportResponse(BaseModel):
    user_id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    status: str
    created_at: Optional[str]
    documents: list[dict]
    consent_records: list[dict]
    exported_at: str


@router.get(
    "/users/{user_id}/export",
    response_model=DataExportResponse,
    summary="GDPR/CCPA データポータビリティ (Art.20)",
    description="ユーザーの全個人データをJSON形式でエクスポートします。",
)
def export_user_data(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Allow admin or the user themselves
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    docs = db.query(Document).filter(Document.owner_id == user_id).all()
    consents = db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).all()

    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="gdpr_data_export",
        resource_type="user",
        resource_id=user_id,
        detail=f"exported data for user {user_id}",
        ip_address=None,
    )

    return DataExportResponse(
        user_id=target_user.id,
        email=target_user.email,
        username=target_user.username,
        full_name=target_user.full_name,
        role=target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role),
        status=target_user.status.value if hasattr(target_user.status, "value") else str(target_user.status),
        created_at=target_user.created_at.isoformat() if target_user.created_at else None,
        exported_at=datetime.now(timezone.utc).isoformat(),
        documents=[
            {
                "id": d.id,
                "title": d.title,
                "document_type": d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type),
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "filename": d.filename,
                "file_size": d.file_size,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "retention_expires_at": d.retention_expires_at.isoformat() if d.retention_expires_at else None,
            }
            for d in docs
        ],
        consent_records=[
            {
                "id": c.id,
                "consent_type": c.consent_type,
                "version": c.version,
                "granted": c.granted,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consents
        ],
    )


# ---------- Consent Management (GDPR Art.7) ----------

class ConsentRequest(BaseModel):
    consent_type: ConsentType
    version: str = "1.0"
    granted: bool
    source: str = "api"
    disclosed_purpose: Optional[str] = None
    disclosed_retention_period: Optional[str] = None
    disclosed_third_parties: Optional[str] = None


class ConsentResponse(BaseModel):
    id: str
    user_id: str
    consent_type: str
    version: str
    granted: bool
    created_at: Optional[str]


@router.post(
    "/consent",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="GDPR 同意記録 (Art.7)",
)
def record_consent(
    body: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = ConsentRecord(
        user_id=current_user.id,
        consent_type=body.consent_type.value,
        version=body.version,
        granted=body.granted,
        source=body.source,
        disclosed_purpose=body.disclosed_purpose,
        disclosed_retention_period=body.disclosed_retention_period,
        disclosed_third_parties=body.disclosed_third_parties,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="consent_recorded",
        resource_type="consent",
        resource_id=record.id,
        detail=f"type={body.consent_type.value} granted={body.granted} v={body.version}",
        ip_address=None,
    )

    return ConsentResponse(
        id=record.id,
        user_id=record.user_id,
        consent_type=record.consent_type,
        version=record.version,
        granted=record.granted,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.get(
    "/consent/{user_id}",
    response_model=list[ConsentResponse],
    summary="GDPR 同意状況確認",
)
def get_consent_status(
    user_id: str,
    consent_type: Optional[ConsentType] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    q = db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id)
    if consent_type:
        q = q.filter(ConsentRecord.consent_type == consent_type.value)
    records = q.order_by(ConsentRecord.created_at.desc()).all()

    return [
        ConsentResponse(
            id=r.id,
            user_id=r.user_id,
            consent_type=r.consent_type,
            version=r.version,
            granted=r.granted,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in records
    ]


# ---------- Physical Deletion Job (Admin) ----------

class DeletionJobResponse(BaseModel):
    processed: int
    deleted_files: int
    errors: int
    grace_days: int
    run_at: str


@router.post(
    "/admin/run-deletion-job",
    response_model=DeletionJobResponse,
    summary="物理削除ジョブ実行 (Admin only)",
    description=(
        "削除フラグ済み文書のうち猶予期間を過ぎたものを物理削除します。"
        "監査ログは保持されます（法的証跡保持義務）。"
    ),
)
def run_deletion_job_endpoint(
    grace_days: int = Query(30, ge=1, le=365, description="猶予期間（日数）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    from services.deletion_job import run_deletion_job
    result = run_deletion_job(db, grace_days=grace_days)
    return DeletionJobResponse(**result)
