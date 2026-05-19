"""M365Setting model — singleton row (id=1) for Microsoft 365 tenant config.

Stores tenant_id / client_id in plaintext and client_secret as Fernet ciphertext.
Singleton is enforced at the DB layer via CHECK (id = 1).
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from database import Base


class M365Setting(Base):
    __tablename__ = "m365_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_m365_settings_singleton"),)

    id = Column(Integer, primary_key=True, default=1)
    tenant_id = Column(String(64), nullable=False, default="")
    client_id = Column(String(64), nullable=False, default="")
    client_secret_enc = Column(Text, nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=False)
    auto_provision = Column(Boolean, nullable=False, default=True)
    default_role = Column(String(16), nullable=False, default="viewer")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)
