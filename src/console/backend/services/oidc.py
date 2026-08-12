"""Entra ID / generic OpenID Connect SSO support (Phase 1).

Implements the authorization-code flow with PKCE:
  1. /auth/oidc/login builds an authorization URL (state JWT carries verifier).
  2. /auth/oidc/callback exchanges the code, validates the id_token via JWKS
     and provisions/links a local user (same policy as the M365 bridge).

MFA is enforced by the identity provider (Entra Conditional Access / HENNGE);
the app never weakens that policy.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Any

import httpx
from jose import JWTError, jwt

from config import settings

logger = logging.getLogger(__name__)


class OIDCConfigError(RuntimeError):
    pass


class OIDCExchangeError(RuntimeError):
    pass


class OIDCValidationError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(
        settings.oidc_client_id
        and settings.oidc_discovery_url
        and settings.oidc_redirect_uri
    )


def _require_config() -> None:
    if not is_configured():
        raise OIDCConfigError(
            "OIDC is not configured: OIDC_CLIENT_ID / OIDC_DISCOVERY_URL / "
            "OIDC_REDIRECT_URI are required"
        )


def _discover() -> dict[str, Any]:
    _require_config()
    try:
        resp = httpx.get(
            settings.oidc_discovery_url, timeout=10.0, follow_redirects=True
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise OIDCConfigError(f"OIDC discovery failed: {exc}") from exc


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sha256_b64url(value: str) -> str:
    return _b64url(hashlib.sha256(value.encode()).digest())


def build_authorization_url(state: str, nonce: str, verifier: str) -> str:
    """Build the authorization endpoint URL with PKCE S256."""
    meta = _discover()
    auth_endpoint = meta.get("authorization_endpoint")
    if not auth_endpoint:
        raise OIDCConfigError("Discovery document has no authorization_endpoint")
    params = {
        "response_type": "code",
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "scope": settings.oidc_scope,
        "state": state,
        "nonce": nonce,
        "code_challenge": _sha256_b64url(verifier),
        "code_challenge_method": "S256",
    }
    import urllib.parse

    return f"{auth_endpoint}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, verifier: str) -> dict[str, Any]:
    """Exchange the authorization code for tokens (client_secret_basic)."""
    meta = _discover()
    token_endpoint = meta.get("token_endpoint")
    if not token_endpoint:
        raise OIDCConfigError("Discovery document has no token_endpoint")
    auth = httpx.BasicAuth(settings.oidc_client_id, settings.oidc_client_secret)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "code_verifier": verifier,
    }
    try:
        resp = httpx.post(token_endpoint, data=data, auth=auth, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise OIDCExchangeError(f"Token exchange failed: {exc}") from exc


def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    try:
        resp = httpx.get(jwks_uri, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise OIDCValidationError(f"JWKS fetch failed: {exc}") from exc


def validate_id_token(id_token: str, nonce: str) -> dict[str, Any]:
    """Validate the id_token signature/iss/aud/exp/nonce and return claims."""
    meta = _discover()
    jwks = _fetch_jwks(meta.get("jwks_uri", ""))
    unverified = jwt.get_unverified_claims(id_token)
    issuer = unverified.get("iss")
    expected_iss = meta.get("issuer")
    if issuer != expected_iss:
        raise OIDCValidationError(f"id_token issuer mismatch: {issuer}")
    if unverified.get("aud") not in (
        settings.oidc_client_id,
        [settings.oidc_client_id],
    ):
        raise OIDCValidationError("id_token audience mismatch")
    if unverified.get("nonce") != nonce:
        raise OIDCValidationError("id_token nonce mismatch")
    try:
        claims = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384"],
            audience=settings.oidc_client_id,
            issuer=expected_iss,
            options={"verify_at_hash": False},
        )
    except JWTError as exc:
        raise OIDCValidationError(f"id_token verification failed: {exc}") from exc
    return claims
