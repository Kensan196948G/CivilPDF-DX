import ipaddress
import os
from datetime import datetime, timezone

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

router = APIRouter(prefix="/auth", tags=["Authentication"])

_M365_ALLOWED_NETWORKS_ENV = "M365_ALLOWED_NETWORKS"


def _is_m365_allowed_ip(ip: str | None) -> bool:
    """Return True if the client IP is within the configured M365 allowed networks.

    When M365_ALLOWED_NETWORKS is not set, all IPs are allowed so that firewall /
    reverse-proxy rules remain the sole enforcement layer (backward-compatible).
    Set M365_ALLOWED_NETWORKS=10.0.0.0/8,192.168.0.0/16 to enforce at the app layer.
    """
    allowed_str = os.environ.get(_M365_ALLOWED_NETWORKS_ENV, "").strip()
    if not allowed_str:
        return True  # unset → allow all; LAN boundary delegated to network layer
    if not ip:
        return False
    try:
        client_ip = ipaddress.ip_address(ip)
        for cidr in allowed_str.split(","):
            cidr = cidr.strip()
            if cidr and client_ip in ipaddress.ip_network(cidr, strict=False):
                return True
    except ValueError:
        return False
    return False


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

    if not _is_m365_allowed_ip(ip):
        _log_audit(
            db, action="m365_login_failed", user_id=None,
            detail=f"network_blocked ip={ip} email={email}", ip=ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="M365 login is not allowed from this network",
        )

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

    entra_id = graph_user.get("id")
    settings_row = m365_service.get_settings_row(db)

    # Resolve by entra_id first (immutable Entra identity), then email as fallback.
    # Prevents mis-binding when a user renames/changes their email in Entra.
    user = None
    if entra_id:
        user = db.query(User).filter(User.entra_id == entra_id).first()
    if user is None:
        user_by_email = db.query(User).filter(User.email == email).first()
        if user_by_email is not None:
            if user_by_email.entra_id and user_by_email.entra_id != entra_id:
                # Conflict: this email row is already claimed by a different Entra identity
                _log_audit(
                    db, action="m365_login_failed", user_id=None,
                    detail=f"identity_conflict email={email} entra_id={entra_id}", ip=ip,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Local account email is bound to a different M365 identity",
                )
            user = user_by_email

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
            entra_id=entra_id,
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
        if entra_id and not user.entra_id:
            user.entra_id = entra_id

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
