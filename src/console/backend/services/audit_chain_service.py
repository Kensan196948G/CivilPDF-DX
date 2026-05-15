"""Hash chain service for tamper-evident audit logs.

Implements a blockchain-inspired hash chain where each AuditLog record
contains the SHA-256 hash of the previous record, creating a chain that
makes tampering detectable.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.audit_log import AuditLog

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64  # sentinel for first record in chain


def _normalize_dt(dt: Optional[datetime]) -> str:
    """Return canonical UTC ISO-8601 string for hashing, regardless of DB storage format."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _compute_record_hash(
    prev_hash: str,
    sequence_number: int,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str],
    resource_id: Optional[str],
    detail: Optional[str],
    ip_address: Optional[str],
    created_at_iso: str,
) -> str:
    """Compute SHA-256 over chain-relevant fields."""
    data = json.dumps(
        {
            "prev_hash": prev_hash,
            "seq": sequence_number,
            "user_id": user_id or "",
            "action": action,
            "resource_type": resource_type or "",
            "resource_id": resource_id or "",
            "detail": detail or "",
            "ip_address": ip_address or "",
            "created_at": created_at_iso,
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(data).hexdigest()


def get_last_record(db: Session) -> Optional[AuditLog]:
    """Return the most recent AuditLog by sequence_number."""
    return (
        db.query(AuditLog)
        .filter(AuditLog.sequence_number != None)  # noqa: E711
        .order_by(AuditLog.sequence_number.desc())
        .first()
    )


def create_chained_audit_log(
    db: Session,
    *,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Create a new AuditLog record with hash chain linkage."""
    last = get_last_record(db)
    prev_hash = last.record_hash if (last and last.record_hash) else GENESIS_HASH
    next_seq = (last.sequence_number + 1) if (last and last.sequence_number is not None) else 1

    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        sequence_number=next_seq,
        prev_hash=prev_hash,
        record_hash="pending",  # placeholder; replaced below after DB assigns created_at
    )
    db.add(log)
    db.flush()   # DB assigns created_at via server_default
    db.refresh(log)  # reload to get the actual DB-stored created_at

    # Compute hash using the exact created_at value stored in DB
    record_hash = _compute_record_hash(
        prev_hash=prev_hash,
        sequence_number=next_seq,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        created_at_iso=_normalize_dt(log.created_at),
    )
    log.record_hash = record_hash
    db.commit()
    db.refresh(log)
    return log


def verify_chain(db: Session, limit: int = 1000) -> dict:
    """Verify the integrity of the hash chain.

    Returns:
    - chain_valid: bool
    - records_checked: int
    - first_broken_sequence: int | None
    - error: str | None
    """
    records = (
        db.query(AuditLog)
        .filter(AuditLog.sequence_number != None)  # noqa: E711
        .order_by(AuditLog.sequence_number.asc())
        .limit(limit)
        .all()
    )

    if not records:
        return {"chain_valid": True, "records_checked": 0, "first_broken_sequence": None, "error": None}

    prev_hash = GENESIS_HASH
    for record in records:
        if record.prev_hash != prev_hash:
            return {
                "chain_valid": False,
                "records_checked": record.sequence_number,
                "first_broken_sequence": record.sequence_number,
                "error": f"prev_hash mismatch at sequence {record.sequence_number}",
            }

        expected_hash = _compute_record_hash(
            prev_hash=record.prev_hash or GENESIS_HASH,
            sequence_number=record.sequence_number,
            user_id=record.user_id,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            detail=record.detail,
            ip_address=record.ip_address,
            created_at_iso=_normalize_dt(record.created_at),
        )

        if record.record_hash != expected_hash:
            return {
                "chain_valid": False,
                "records_checked": record.sequence_number,
                "first_broken_sequence": record.sequence_number,
                "error": f"record_hash tampered at sequence {record.sequence_number}",
            }

        prev_hash = record.record_hash

    return {
        "chain_valid": True,
        "records_checked": len(records),
        "first_broken_sequence": None,
        "error": None,
    }
