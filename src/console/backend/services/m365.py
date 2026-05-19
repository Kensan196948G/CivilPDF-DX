"""Microsoft 365 service layer — secret encryption, MSAL token, Graph lookup.

Design ref: docs/architecture/m365-auth-design.md
- Fernet (cryptography) encrypts client_secret at rest (column m365_settings.client_secret_enc).
- MSAL Client Credentials Flow acquires an app-only token against the configured tenant.
- MS Graph /users/{email} verifies the M365 account exists; the response is the
  bridging fact used to issue a CivilPDF-DX JWT (role/permission decisions
  always come from the local DB, not from Graph).
"""

from __future__ import annotations

from typing import Optional, Tuple

import httpx
import msal
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from config import settings
from models.m365_setting import M365Setting


GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_USER_URL = "https://graph.microsoft.com/v1.0/users/{email}"


class M365ConfigError(RuntimeError):
    """Raised when M365 is not enabled or not fully configured."""


class M365AuthError(RuntimeError):
    """Raised when MSAL or Graph rejects the configured credentials."""


class M365UserNotFound(RuntimeError):
    """Raised when the email is not present in the configured M365 tenant."""


def _fernet() -> Fernet:
    key = settings.m365_fernet_key
    if not key:
        raise M365ConfigError("M365_FERNET_KEY is not configured")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        raise M365ConfigError(f"Invalid M365_FERNET_KEY: {exc}") from exc


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a client_secret for storage in m365_settings.client_secret_enc."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a stored client_secret. Returns empty string for empty input."""
    if not ciphertext:
        return ""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise M365ConfigError("Stored client_secret cannot be decrypted") from exc


def get_settings_row(db: Session) -> M365Setting:
    """Fetch the singleton m365_settings row, creating it if missing."""
    row = db.query(M365Setting).filter(M365Setting.id == 1).first()
    if row is None:
        row = M365Setting(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _require_enabled(row: M365Setting) -> Tuple[str, str, str]:
    if not row.enabled:
        raise M365ConfigError("M365 integration is disabled")
    if not (row.tenant_id and row.client_id and row.client_secret_enc):
        raise M365ConfigError("M365 tenant/client credentials are not configured")
    return row.tenant_id, row.client_id, decrypt_secret(row.client_secret_enc)


def acquire_app_token(db: Session) -> str:
    """Acquire an app-only access token via MSAL Client Credentials Flow."""
    row = get_settings_row(db)
    tenant_id, client_id, client_secret = _require_enabled(row)

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )
    result = app.acquire_token_for_client(scopes=[GRAPH_SCOPE])
    if "access_token" not in result:
        err = result.get("error_description") or result.get("error") or "unknown_error"
        raise M365AuthError(f"MSAL token acquisition failed: {err}")
    return result["access_token"]


def lookup_user(db: Session, email: str) -> dict:
    """Look up a user in MS Graph by email/UPN. Returns selected fields.

    Raises M365UserNotFound on 404, M365AuthError on 401/403, other HTTP errors propagate.
    """
    if not email:
        raise M365UserNotFound("email is required")
    token = acquire_app_token(db)
    url = GRAPH_USER_URL.format(email=email)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            url,
            headers=headers,
            params={"$select": "id,displayName,userPrincipalName,mail,accountEnabled"},
        )
    if resp.status_code == 404:
        raise M365UserNotFound(email)
    if resp.status_code in (401, 403):
        raise M365AuthError(f"Graph rejected the request: HTTP {resp.status_code}")
    resp.raise_for_status()
    data = resp.json()
    return {
        "id": data.get("id"),
        "display_name": data.get("displayName"),
        "user_principal_name": data.get("userPrincipalName"),
        "mail": data.get("mail"),
        "account_enabled": data.get("accountEnabled", True),
    }


def test_connection(db: Session) -> dict:
    """Probe the configured credentials by acquiring a token only.

    Used by the admin UI's "Test connection" button. Never raises — returns
    a diagnostic dict the API layer can surface as JSON.
    """
    try:
        acquire_app_token(db)
    except M365ConfigError as exc:
        return {"ok": False, "stage": "config", "detail": str(exc)}
    except M365AuthError as exc:
        return {"ok": False, "stage": "msal", "detail": str(exc)}
    except Exception as exc:  # noqa: BLE001 — diagnostic catch-all for UI feedback
        return {"ok": False, "stage": "unknown", "detail": str(exc)}
    return {"ok": True, "stage": "msal", "detail": "token acquired"}


def update_settings(
    db: Session,
    *,
    tenant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    enabled: Optional[bool] = None,
    auto_provision: Optional[bool] = None,
    default_role: Optional[str] = None,
    updated_by: Optional[str] = None,
) -> M365Setting:
    """Update the singleton m365_settings row. client_secret is encrypted on write."""
    row = get_settings_row(db)
    if tenant_id is not None:
        row.tenant_id = tenant_id
    if client_id is not None:
        row.client_id = client_id
    if client_secret is not None:
        row.client_secret_enc = encrypt_secret(client_secret)
    if enabled is not None:
        row.enabled = enabled
    if auto_provision is not None:
        row.auto_provision = auto_provision
    if default_role is not None:
        row.default_role = default_role
    if updated_by is not None:
        row.updated_by = updated_by
    db.commit()
    db.refresh(row)
    return row
