import os
import uuid
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    status,
)
from sqlalchemy.orm import Session
from typing import List, Optional
import aiofiles

from database import get_db
from models.user import User
from models.document import Document, DocumentStatus, DocumentType
from auth.dependencies import get_current_user
from api.schemas import DocumentResponse, DocumentUpdate
from config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_FILE_BYTES = settings.max_file_size_mb * 1024 * 1024


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    project_id: Optional[str] = Query(None),
    document_type: Optional[DocumentType] = Query(None),
    status_filter: Optional[DocumentStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Document)
    if project_id:
        q = q.filter(Document.project_id == project_id)
    if document_type:
        q = q.filter(Document.document_type == document_type)
    if status_filter:
        q = q.filter(Document.status == status_filter)

    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return items


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str = Form(...),
    title: str = Form(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are allowed",
        )

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {settings.max_file_size_mb}MB limit",
        )

    # Save file
    upload_dir = Path(settings.upload_dir) / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.pdf"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    doc = Document(
        title=title,
        document_type=document_type,
        filename=file.filename or "upload.pdf",
        file_path=str(file_path),
        file_size=len(content),
        mime_type="application/pdf",
        project_id=project_id,
        owner_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return doc


@router.patch("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: str,
    body: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if doc.owner_id != current_user.id and current_user.role.value not in (
        "admin",
        "manager",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if doc.owner_id != current_user.id and current_user.role.value not in (
        "admin",
        "manager",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.delete(doc)
    db.commit()
