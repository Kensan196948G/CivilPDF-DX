from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


class AuditLog(Base):
    """Append-only audit log with SHA-256 hash chain.

    Implements tamper-evident logging required by:
    - NIS2 Directive (Article 21 security measures)
    - ISO 19650-5 (information security management)
    - J-SOX (log integrity requirements)

    Chain structure: each record stores SHA-256(prev_hash + current_record_data).
    Any tampering breaks the chain and is detected by /api/v1/audit-logs/verify.
    """

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True, index=True)
    resource_id = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Hash chain fields (NIS2/ISO 19650/J-SOX)
    sequence_number = Column(Integer, nullable=True, index=True)  # monotonic sequence
    record_hash = Column(String, nullable=True)  # SHA-256 of this record's data
    prev_hash = Column(String, nullable=True)  # SHA-256 of previous record (chain link)

    user = relationship("User", foreign_keys=[user_id])
