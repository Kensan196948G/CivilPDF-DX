from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from config import settings
from database import get_db
from models.user import User, UserRole
from auth.jwt import decode_token

# auto_error=False: returns None instead of 401 when no token is present,
# allowing the debug bypass below to kick in.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

_DEV_USER_ID = "dev-admin-00000000-0000-0000-0000-000000000000"


def _get_or_create_dev_user(db: Session) -> User:
    """Return (and lazily create) the singleton dev-bypass admin user."""
    from sqlalchemy.exc import IntegrityError

    user = db.query(User).filter(User.id == _DEV_USER_ID).first()
    if user is not None:
        return user

    try:
        user = User(
            id=_DEV_USER_ID,
            email="dev@civildx.local",
            username="dev-admin",
            full_name="Dev Admin (bypass)",
            hashed_password=None,
            role=UserRole.ADMIN,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        # Another worker may have inserted the row concurrently.
        db.rollback()
        user = db.query(User).filter(User.id == _DEV_USER_ID).first()

    return user


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Development bypass: when DEBUG=true and no token supplied, use dev admin.
    if settings.debug and token is None:
        return _get_or_create_dev_user(db)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token, expected_type="access")
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin required"
        )
    return current_user


def require_manager(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Manager or Admin required"
        )
    return current_user
