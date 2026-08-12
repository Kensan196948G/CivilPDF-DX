"""In-app notification helpers (Phase 1)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: str,
    notification_type: str,
    title: str,
    body: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> Notification:
    """Create a notification row (no commit; caller controls the transaction)."""
    record = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        resource_type=resource_type,
        resource_id=resource_id,
        is_read=False,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    return record
