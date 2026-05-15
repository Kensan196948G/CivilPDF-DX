from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserRole, UserStatus
from models.audit_log import AuditLog
from auth.jwt import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from auth.dependencies import get_current_user
from api.schemas import TokenResponse, TokenRefreshRequest, UserResponse
from services import m365 as m365_service
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])


class M365LoginRequest(BaseModel):
    email: EmailStr


def _log_audit(
    db: Session,
    *,
    action: str,
    user_id: str | None,
    detail: str,
    ip: str | None,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type="auth",
            detail=detail,
            ip_address=ip,
        )
    )
    db.commit()


@router.post("/token", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/m365/login", response_model=TokenResponse)
def login_m365(
    body: M365LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Non-interactive M365 login bridge.

    The frontend posts the user's email; backend verifies via MS Graph that
    the email exists in the configured tenant (Client Credentials Flow),
    then issues a CivilPDF-DX JWT. If auto_provision is on and no local
    User row exists, a viewer-role user is created.

    Trust model: this endpoint is intended for **LAN-restricted deployments**
    (see docs/architecture/m365-auth-design.md §3). Spoofing is mitigated by
    network boundary + full audit logging, not by interactive MS sign-in.
    """
    email = body.email.lower()
    ip = request.client.host if request.client else None

    try:
        graph_user = m365_service.lookup_user(db, email)
    except m365_service.M365ConfigError as exc:
        _log_audit(
            db, action="m365_login_failed", user_id=None,
            detail=f"config_error: {exc} ({email})", ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except m365_service.M365UserNotFound:
        _log_audit(
            db, action="m365_user_not_found", user_id=None,
            detail=f"email={email}", ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="M365 account not found in tenant",
        )
    except m365_service.M365AuthError as exc:
        _log_audit(
            db, action="m365_login_failed", user_id=None,
            detail=f"auth_error: {exc} ({email})", ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    if not graph_user.get("account_enabled", True):
        _log_audit(
            db, action="m365_login_failed", user_id=None,
            detail=f"account_disabled email={email}", ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="M365 account is disabled",
        )

    user = db.query(User).filter(User.email == email).first()
    settings_row = m365_service.get_settings_row(db)

    if user is None:
        if not settings_row.auto_provision:
            _log_audit(
                db, action="m365_login_failed", user_id=None,
                detail=f"no_local_user_and_auto_provision_off email={email}", ip=ip,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No local account for this M365 user",
            )
        try:
            role = UserRole(settings_row.default_role or "viewer")
        except ValueError:
            role = UserRole.VIEWER
        user = User(
            email=email,
            username=email.split("@", 1)[0],
            full_name=graph_user.get("display_name") or email,
            role=role,
            status=UserStatus.ACTIVE,
            entra_id=graph_user.get("id"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _log_audit(
            db, action="m365_user_provisioned", user_id=user.id,
            detail=f"role={role.value} email={email}", ip=ip,
        )
    else:
        if user.status != UserStatus.ACTIVE.value and user.status != UserStatus.ACTIVE:
            _log_audit(
                db, action="m365_login_failed", user_id=user.id,
                detail=f"local_account_not_active status={user.status}", ip=ip,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )
        if not user.entra_id and graph_user.get("id"):
            user.entra_id = graph_user["id"]

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    token_data = {"sub": user.id, "email": user.email, "role": role_value}
    _log_audit(
        db, action="m365_login_success", user_id=user.id,
        detail=f"email={email}", ip=ip,
    )
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
