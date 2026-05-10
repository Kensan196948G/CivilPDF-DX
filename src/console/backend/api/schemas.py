from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from models.user import UserRole, UserStatus
from models.document import DocumentStatus, DocumentType


# ─── Auth ───
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


# ─── User ───
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.ENGINEER

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Project ───
class ProjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Document ───
class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: DocumentType
    status: DocumentStatus
    filename: str
    file_size: int
    page_count: Optional[int]
    is_pdfa: bool
    tags: List[str] = []
    project_id: str
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    document_type: Optional[DocumentType] = None
    tags: Optional[List[str]] = None


# ─── Workflow ───
class WorkflowCreate(BaseModel):
    document_id: str
    approver_ids: List[str]


class ApprovalStepResponse(BaseModel):
    id: str
    order: int
    status: str
    comment: Optional[str]
    decided_at: Optional[datetime]
    approver: UserResponse

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    id: str
    document_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    steps: List[ApprovalStepResponse]

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    decision: str  # "approve" or "reject"
    comment: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("decision must be 'approve' or 'reject'")
        return v


# ─── Pagination ───
class PaginatedResponse(BaseModel):
    items: List
    total: int
    page: int
    per_page: int
    pages: int
