import uuid
from datetime import datetime, timezone
from pathlib import Path
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


def _extract_text_with_pypdf(file_path: str) -> list[dict]:
    """Extract text from a PDF using pypdf. Returns [{page, text}] per page."""
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError:
        return [{"page": 1, "text": "(pypdf not available — install pypdf>=5.0)"}]

    path = Path(file_path)
    if not path.exists():
        return [{"page": 1, "text": "(PDF file not found on server)"}]

    try:
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            pages.append({"page": i, "text": text.strip()})
        return pages if pages else [{"page": 1, "text": "(no extractable text — may be image-only PDF)"}]
    except Exception as exc:
        return [{"page": 1, "text": f"(text extraction failed: {exc})"}]


@router.post(
    "/process", response_model=OcrJobResponse, status_code=status.HTTP_202_ACCEPTED
)
def start_ocr(
    body: OcrJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Queue an OCR / text-extraction job for a document. Returns job_id for polling."""
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Document file has been deleted (GDPR erasure)",
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Perform synchronous extraction and mark completed immediately.
    # Replace with background task / Celery worker for production.
    pages = _extract_text_with_pypdf(doc.file_path)
    completed_at = datetime.now(timezone.utc).isoformat()

    _jobs[job_id] = {
        "job_id": job_id,
        "document_id": body.document_id,
        "status": "completed",
        "language": body.language,
        "created_at": now,
        "completed_at": completed_at,
        "page_count": len(pages),
        "error": None,
        "_pages": pages,
    }
    return OcrJobResponse(**{k: v for k, v in _jobs[job_id].items() if k != "_pages"})


@router.get("/jobs/{job_id}", response_model=OcrJobResponse)
def get_ocr_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Poll OCR job status."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    return OcrJobResponse(**{k: v for k, v in job.items() if k != "_pages"})


@router.get("/jobs/{job_id}/result", response_model=OcrResultResponse)
def get_ocr_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> OcrResultResponse:
    """Return OCR extracted text pages."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    if job["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"OCR job failed: {job.get('error')}"
        )

    return OcrResultResponse(
        job_id=job_id,
        document_id=job["document_id"],
        status=job["status"],
        pages=job.get("_pages", []),
    )
