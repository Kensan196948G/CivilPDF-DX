import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.document import Document
from models.user import User

router = APIRouter(prefix="/ocr", tags=["OCR"])

# In-memory job store — replace with DB/Redis in production
_jobs: dict[str, dict] = {}


class OcrJobRequest(BaseModel):
    document_id: str
    language: str = "jpn"
    enable_vertical: bool = True


class OcrJobResponse(BaseModel):
    job_id: str
    document_id: str
    status: str  # queued | processing | completed | failed
    language: str
    created_at: str
    completed_at: Optional[str] = None
    page_count: Optional[int] = None
    error: Optional[str] = None


class OcrResultResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    pages: list[dict]  # [{page: int, text: str}]


@router.post("/process", response_model=OcrJobResponse, status_code=status.HTTP_202_ACCEPTED)
def start_ocr(
    body: OcrJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Queue an OCR job for a document. Returns job_id for status polling."""
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    _jobs[job_id] = {
        "job_id": job_id,
        "document_id": body.document_id,
        "status": "queued",
        "language": body.language,
        "created_at": now,
        "completed_at": None,
        "page_count": doc.page_count,
        "error": None,
    }
    return OcrJobResponse(**_jobs[job_id])


@router.get("/jobs/{job_id}", response_model=OcrJobResponse)
def get_ocr_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Poll OCR job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found")
    return OcrJobResponse(**job)


@router.get("/jobs/{job_id}/result", response_model=OcrResultResponse)
def get_ocr_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> OcrResultResponse:
    """Return OCR extracted text. Returns stub data until Tesseract is integrated."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found")
    if job["status"] not in ("completed", "queued", "processing"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="OCR job not completed")

    # Stub result — real Tesseract integration will populate this
    return OcrResultResponse(
        job_id=job_id,
        document_id=job["document_id"],
        status=job["status"],
        pages=[{"page": 1, "text": "(OCR テキスト抽出はTesseract統合後に有効になります)"}],
    )
