from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# Many-to-many: users <-> projects
user_projects = Table(
    "user_projects",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id")),
    Column("project_id", String, ForeignKey("projects.id")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)  # nullable for SSO users
    role = Column(Enum(UserRole), default=UserRole.ENGINEER)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)

    # SSO
    entra_id = Column(String, nullable=True, unique=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relations
    projects = relationship(
        "Project", secondary=user_projects, back_populates="members"
    )
    documents = relationship("Document", back_populates="owner")
    approvals = relationship("ApprovalStep", back_populates="approver")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)  # 工事番号
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    members = relationship("User", secondary=user_projects, back_populates="projects")
    documents = relationship("Document", back_populates="project")
