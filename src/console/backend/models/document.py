from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class DocumentType(str, enum.Enum):
    DRAWING = "drawing"  # 図面
    PHOTO = "photo"  # 写真台帳
    INSPECTION = "inspection"  # 検査記録
    SAFETY = "safety"  # 安全書類
    CONTRACT = "contract"  # 契約書
    REPORT = "report"  # 報告書
    CORRECTION = "correction"  # 是正指示書
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    document_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)

    # File info
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    page_count = Column(Integer, nullable=True)
    mime_type = Column(String, default="application/pdf")

    # PDF/A compliance
    is_pdfa = Column(Boolean, default=False)
    pdfa_version = Column(String, nullable=True)  # "PDF/A-1b", "PDF/A-2b", etc.

    # OCR
    ocr_text = Column(Text, nullable=True)
    ocr_processed = Column(Boolean, default=False)

    # Custom metadata (avoiding SQLAlchemy reserved name)
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)

    # Relations
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    project = relationship("Project", back_populates="documents")
    owner = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document")
    workflow = relationship(
        "ApprovalWorkflow", back_populates="document", uselist=False
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    change_note = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="versions")


class ApprovalWorkflow(Base):
    __tablename__ = "approval_workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String, ForeignKey("documents.id"), unique=True, nullable=False
    )
    status = Column(
        String, default="pending"
    )  # pending, in_progress, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="workflow")
    steps = relationship(
        "ApprovalStep", back_populates="workflow", order_by="ApprovalStep.order"
    )


class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("approval_workflows.id"), nullable=False)
    approver_id = Column(String, ForeignKey("users.id"), nullable=False)
    order = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("ApprovalWorkflow", back_populates="steps")
    approver = relationship("User", back_populates="approvals")
