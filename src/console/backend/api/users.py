from fastapi import APIRouter, Depends, HTTPException, status
import json
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from auth.dependencies import get_current_user, require_admin
from auth.jwt import get_password_hash
from api.schemas import UserCreate, UserUpdate, UserResponse
from services.audit_chain_service import create_chained_audit_log
from models.document import Document

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
