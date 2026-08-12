import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
import json
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from auth.dependencies import get_current_user, require_admin
from auth.jwt import get_password_hash
from api.schemas import (
    AdminPasswordResetRequest,
    UserCreate,
    UserUpdate,
    UserResponse,
)
from services.audit_chain_service import create_chained_audit_log
from models.document import Document
from services.notification_service import create_notification

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(User).all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )

    user = User(
        email=body.email,
        username=body.username,
        full_name=body.full_name,
        hashed_password=get_password_hash(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="user.created",
        resource_type="user",
        resource_id=user.id,
        detail=json.dumps(
            {"email": user.email, "role": user.role.value}, ensure_ascii=False
        ),
        ip_address=None,
    )
    return user


@router.get("/permissions-report", response_model=None)
def permissions_report(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin-only permission inventory: users × role × status × organization × projects."""
    rows = []
    for user in db.query(User).order_by(User.email).all():
        rows.append(
            {
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": (
                    user.role.value if hasattr(user.role, "value") else str(user.role)
                ),
                "status": (
                    user.status.value
                    if hasattr(user.status, "value")
                    else str(user.status)
                ),
                "organization_id": user.organization_id or "",
                "project_codes": "|".join(sorted(p.code for p in user.projects)),
                "project_count": len(user.projects),
                "entra_id": user.entra_id or "",
                "last_login": user.last_login.isoformat() if user.last_login else "",
            }
        )
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="admin.permissions_report_exported",
        resource_type="system",
        resource_id="permissions-report",
        detail=json.dumps({"format": format, "rows": len(rows)}),
        ip_address=None,
    )
    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
        payload = "\ufeff" + buf.getvalue()
        from fastapi.responses import Response

        return Response(
            content=payload,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="permissions-report.csv"'
            },
        )
    return {"items": rows, "total": len(rows)}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    if body.unlock:
        user.failed_login_attempts = 0
        user.locked_until = None
    db.commit()
    db.refresh(user)
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="user.updated",
        resource_type="user",
        resource_id=user_id,
        detail=json.dumps(body.model_dump(exclude_none=True), ensure_ascii=False),
        ip_address=None,
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    owned_docs = db.query(Document.id).filter(Document.owner_id == user_id).first()
    if owned_docs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "User owns documents; deactivate the account instead of deleting "
                "to preserve document ownership and audit integrity"
            ),
        )
    db.delete(user)
    db.commit()
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="user.deleted",
        resource_type="user",
        resource_id=user_id,
        detail=json.dumps({"email": user.email}, ensure_ascii=False),
        ip_address=None,
    )


@router.post("/{user_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def admin_reset_password(
    user_id: str,
    body: AdminPasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin resets a user's password (operational path until email is wired)."""
    if (
        len(body.new_password) < 8
        or sum(
            [
                any(c.islower() for c in body.new_password),
                any(c.isupper() for c in body.new_password),
                any(c.isdigit() for c in body.new_password),
                any(not c.isalnum() for c in body.new_password),
            ]
        )
        < 2
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "New password must be at least 8 characters and contain "
                "at least two of: lowercase, uppercase, digits, symbols"
            ),
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user.hashed_password = get_password_hash(body.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="user.password_reset_by_admin",
        resource_type="user",
        resource_id=user_id,
        detail=json.dumps({"target_email": user.email}, ensure_ascii=False),
        ip_address=None,
    )
    create_notification(
        db,
        user_id=user.id,
        notification_type="account.security",
        title="パスワードが再設定されました",
        body="管理者によってパスワードが再設定されました。次回ログイン時に変更してください。",
        resource_type="user",
        resource_id=user.id,
    )
    db.commit()
