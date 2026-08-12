"""Notification center API (Phase 1)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.notification import Notification
from models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    is_read: bool
    created_at: Optional[str]

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    unread: int


def _to_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id,
        notification_type=n.notification_type,
        title=n.title,
        body=n.body,
        resource_type=n.resource_type,
        resource_id=n.resource_id,
        is_read=n.is_read,
        created_at=n.created_at.isoformat() if n.created_at else None,
    )


@router.get("/", response_model=dict)
def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    total = q.count()
    items = (
        q.order_by(Notification.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    import math

    return {
        "items": [_to_response(n) for n in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total else 0,
    }


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UnreadCountResponse:
    unread = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .count()
    )
    return UnreadCountResponse(unread=unread)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    record = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    record.is_read = True
    db.commit()
    db.refresh(record)
    return _to_response(record)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
