from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class OrgType(str, enum.Enum):
    HEADQUARTERS = "headquarters"  # 本社
    BRANCH = "branch"  # 支店
    SITE_OFFICE = "site_office"  # 現場事務所
    MOBILE = "mobile"  # モバイル（持ち出し）


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)  # 組織コード
    org_type = Column(Enum(OrgType), nullable=False, default=OrgType.SITE_OFFICE)

    # Self-referential hierarchy: parent_id=None means root (headquarters)
    parent_id = Column(String, ForeignKey("organizations.id"), nullable=True)

    # Materialized path for efficient subtree queries: e.g. "/hq-id/branch-id/site-id"
    path = Column(String, nullable=False, default="/")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    parent = relationship(
        "Organization", remote_side="Organization.id", back_populates="children"
    )
    children = relationship("Organization", back_populates="parent")
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
