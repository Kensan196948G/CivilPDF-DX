"""Microsoft 365 integration stubs.

These endpoints expose config management and user lookup for the M365
integration UI. Actual AAD / MSAL flows are handled by the desktop app;
the console stores org-level M365 config and exposes a lookup endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from models.user import User
from auth.dependencies import require_admin

router = APIRouter(prefix="/m365", tags=["M365"])

# In-memory config store (replace with DB column in a future migration)
_m365_config: dict = {
    "tenant_id": "",
    "client_id": "",
    "enabled": False,
}


class M365Config(BaseModel):
    tenant_id: str
    client_id: str
    enabled: bool


class M365ConfigUpdate(BaseModel):
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None  # write-only, never returned
    enabled: Optional[bool] = None


@router.get("/config", response_model=M365Config)
def get_m365_config(current_user: User = Depends(require_admin)):
    return M365Config(**_m365_config)


@router.put("/config", response_model=M365Config)
def update_m365_config(
    body: M365ConfigUpdate,
    current_user: User = Depends(require_admin),
):
    if body.tenant_id is not None:
        _m365_config["tenant_id"] = body.tenant_id
    if body.client_id is not None:
        _m365_config["client_id"] = body.client_id
    if body.enabled is not None:
        _m365_config["enabled"] = body.enabled
    return M365Config(**_m365_config)


@router.get("/users/lookup")
def lookup_m365_user(
    email: str,
    current_user: User = Depends(require_admin),
):
    """Check whether an M365 account exists for the given email.

    Returns a stub response — wire to Graph API when tenant credentials
    are configured.
    """
    if not _m365_config.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="M365 integration is not enabled",
        )
    # Stub: real implementation calls MS Graph /users/{email}
    return {"email": email, "exists": False, "display_name": None}
