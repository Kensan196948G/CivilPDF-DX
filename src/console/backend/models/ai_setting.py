"""AI configuration — singleton DB row for Anthropic API key and model settings."""

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


class AiSetting(Base):
    __tablename__ = "ai_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_ai_settings_singleton"),)

    id = Column(Integer, primary_key=True, default=1)
    api_key_enc = Column(Text, nullable=False, default="")  # Fernet ciphertext
    model_name = Column(
        String(128), nullable=False, default="claude-haiku-4-5-20251001"
    )
    enabled = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)
