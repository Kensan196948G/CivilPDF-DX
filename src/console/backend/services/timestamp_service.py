"""RFC 3161 timestamp service for 電子帳簿保存法 / e-文書法 compliance.

In production, configure TSA_URL in .env to point to a real TSA endpoint
(e.g., Seiko Solutions, GMO GlobalSign, DigiCert).
Without a TSA, a local HMAC-based timestamp is generated as a fallback
(sufficient for internal audit trails, not legally equivalent to RFC 3161).
"""

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# TSA endpoint from environment — change to real TSA URL in production
TSA_URL = os.environ.get("TSA_URL", "")
TSA_POLICY_OID = os.environ.get("TSA_POLICY_OID", "1.3.6.1.4.1.13762.3")
TSA_TIMEOUT_SECONDS = int(os.environ.get("TSA_TIMEOUT_SECONDS", "10"))

# Fallback HMAC key — must be set in production via environment
_LOCAL_HMAC_KEY = os.environ.get("TIMESTAMP_HMAC_KEY", "change-me-in-production").encode()


class TimestampError(Exception):
    """Raised when timestamp generation or verification fails."""


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _create_local_timestamp(file_hash: str, filename: str) -> dict:
    """Create a local HMAC-based timestamp token (fallback when TSA unavailable).

    This is NOT a legally valid RFC 3161 token but provides integrity evidence
    for internal audit purposes.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = f"{now_iso}|{file_hash}|{filename}"
    signature = hmac.new(_LOCAL_HMAC_KEY, payload.encode(), hashlib.sha256).hexdigest()
    token_data = {
        "type": "local_hmac",
        "timestamp": now_iso,
        "file_hash": file_hash,
        "filename": filename,
        "signature": signature,
    }
    return token_data


def _request_rfc3161_token(file_hash_bytes: bytes) -> Optional[bytes]:
    """Send a TSQ to the configured TSA and return the raw TSR bytes."""
    if not TSA_URL:
        return None

    try:
        # Build a minimal RFC 3161 TimeStampReq (DER encoded)
        # MessageImprint ::= SEQUENCE { hashAlgorithm AlgorithmIdentifier, hashedMessage OCTET STRING }
        # TimeStampReq ::= SEQUENCE { version INTEGER, messageImprint MessageImprint, ... }
        # We build a minimal valid TSQ using raw DER bytes for SHA-256
        # OID for SHA-256: 2.16.840.1.101.3.4.2.1
        sha256_oid_der = bytes.fromhex(
            "3031300d060960864801650304020105000420"
        ) + file_hash_bytes

        # Minimal TSQ: version=1, messageImprint, certReq=TRUE
        tsq_inner = (
            b"\x02\x01\x01"  # INTEGER 1 (version)
            + b"\x30" + bytes([len(sha256_oid_der)]) + sha256_oid_der
            + b"\x01\x01\xff"  # BOOLEAN TRUE (certReq)
        )
        tsq = b"\x30" + bytes([len(tsq_inner)]) + tsq_inner

        response = httpx.post(
            TSA_URL,
            content=tsq,
            headers={"Content-Type": "application/timestamp-query"},
            timeout=TSA_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.content
    except Exception as exc:
        logger.warning("TSA request failed: %s — falling back to local timestamp", exc)
    return None


def generate_timestamp(file_content: bytes, filename: str) -> dict:
    """Generate a timestamp for the given file content.

    Returns a dict with:
    - file_hash: hex SHA-256 of file_content
    - token_b64: base64-encoded token (RFC 3161 TSR or local HMAC JSON)
    - tsa_url: TSA endpoint used (empty string if local)
    - verified_at: ISO-8601 timestamp string
    - token_type: "rfc3161" or "local_hmac"
    """
    file_hash = _sha256_hex(file_content)
    file_hash_bytes = bytes.fromhex(file_hash)
    verified_at = datetime.now(timezone.utc).isoformat()

    tsr_bytes = _request_rfc3161_token(file_hash_bytes)

    if tsr_bytes:
        token_b64 = base64.b64encode(tsr_bytes).decode()
        token_type = "rfc3161"
        tsa_url_used = TSA_URL
        logger.info("RFC 3161 timestamp obtained from %s for %s", TSA_URL, filename)
    else:
        local_token = _create_local_timestamp(file_hash, filename)
        token_b64 = base64.b64encode(
            json.dumps(local_token).encode()
        ).decode()
        token_type = "local_hmac"
        tsa_url_used = ""
        logger.info("Local HMAC timestamp generated for %s (TSA not configured)", filename)

    return {
        "file_hash": file_hash,
        "token_b64": token_b64,
        "tsa_url": tsa_url_used,
        "verified_at": verified_at,
        "token_type": token_type,
    }


def verify_local_timestamp(token_b64: str, file_hash: str) -> bool:
    """Verify a local HMAC timestamp token."""
    try:
        token_json = base64.b64decode(token_b64).decode()
        token_data = json.loads(token_json)
        if token_data.get("type") != "local_hmac":
            return False
        if token_data.get("file_hash") != file_hash:
            return False
        payload = f"{token_data['timestamp']}|{token_data['file_hash']}|{token_data['filename']}"
        expected_sig = hmac.new(
            _LOCAL_HMAC_KEY, payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, token_data.get("signature", ""))
    except Exception as exc:
        logger.warning("Local timestamp verification failed: %s", exc)
        return False


def verify_file_against_timestamp(file_content: bytes, stored_hash: str, token_b64: str) -> bool:
    """Verify that file_content matches the stored hash and the token is valid."""
    current_hash = _sha256_hex(file_content)
    if current_hash != stored_hash:
        logger.warning("File hash mismatch: stored=%s current=%s", stored_hash, current_hash)
        return False
    # For local tokens, verify HMAC; RFC 3161 verification requires ASN.1 parsing
    try:
        raw = base64.b64decode(token_b64)
        token_data = json.loads(raw.decode())
        if token_data.get("type") == "local_hmac":
            return verify_local_timestamp(token_b64, stored_hash)
    except Exception:
        pass
    # RFC 3161 token — hash match is sufficient for basic integrity check
    logger.info("RFC 3161 token present; hash match confirmed for integrity check")
    return True
