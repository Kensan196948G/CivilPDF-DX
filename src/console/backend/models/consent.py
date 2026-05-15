"""Consent management model — GDPR Article 7 compliance."""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class ConsentType(str, enum.Enum):
    PRIVACY_POLICY = "privacy_policy"
    DATA_PROCESSING = "data_processing"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    DATA_TRANSFER_THIRD_PARTY = "data_transfer_third_party"
    DATA_TRANSFER_INTERNATIONAL = "data_transfer_international"


class ConsentRecord(Base):
    """Immutable consent audit trail.

    Implements GDPR Art.7 (conditions for consent) and Art.17 (right to erasure).
    Each row is append-only: revocations are new rows with granted=False,
    not updates to existing rows — preserving the full consent history.
    """

    __tablename__ = "consent_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    consent_type = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, default="1.0")  # policy version
    granted = Column(Boolean, nullable=False)  # True=同意, False=撤回

    # Context at time of consent
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    source = Column(String, nullable=True)  # "web_ui", "api", "admin_portal"

    # GDPR Art.13: what was disclosed to the user when consent was given
    disclosed_purpose = Column(Text, nullable=True)
    disclosed_retention_period = Column(String, nullable=True)
    disclosed_third_parties = Column(Text, nullable=True)

    # Timestamp is immutable once created — no onupdate
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", foreign_keys=[user_id])
