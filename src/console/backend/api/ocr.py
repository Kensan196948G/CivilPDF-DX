"""Document text extraction (the ``/ocr`` endpoints).

IMPORTANT — what this actually is
---------------------------------
The console performs **PDF text-layer extraction** (pypdf), not OCR. No OCR
engine is a dependency, so an image-only scan — the common case for 建設 図面 —
cannot be recognised here. The response therefore reports ``engine`` and uses
``status="unsupported"`` when there is no text layer, instead of returning a
placeholder sentence that looked like extracted text. ``language`` and
``enable_vertical`` are accepted for forward compatibility and echoed back, but
the current engine does not use them (it returns the text layer verbatim).

Jobs are persisted (``ocr_jobs``) so they are shared between uvicorn workers and
survive a restart; they used to live in a module-level dict.

Access follows the document's visibility (``assert_document_visible``), the same
rule every other document endpoint applies, so a user cannot read another
organization's document text through this API.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models.document import Document
from models.ocr_job import (
    OCR_ENGINE_TEXT_LAYER,
    OCR_STATUS_COMPLETED,
    OCR_STATUS_FAILED,
    OCR_STATUS_UNSUPPORTED,
    OcrJob,
)
from models.user import User
from services.access_control import assert_document_visible

router = APIRouter(prefix="/ocr", tags=["OCR"])

# Shown when the PDF has no text layer: the caller must not mistake this for
# extracted content.
_NO_TEXT_LAYER_MESSAGE = (
    "PDFにテキストレイヤがありません（画像のみのPDF）。"
    "本APIはテキスト抽出のみで、OCRエンジンは未導入のため文字認識できません。"
)


class OcrJobRequest(BaseModel):
    document_id: str
    language: str = "jpn"
    enable_vertical: bool = True


class OcrJobResponse(BaseModel):
    job_id: str
    document_id: str
    status: str  # completed | unsupported | failed
    engine: str
    language: str
    enable_vertical: bool
    created_at: str
    completed_at: str | None = None
    page_count: int | None = None
    error: str | None = None


class OcrResultResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    engine: str
    pages: list[dict]  # [{page: int, text: str}] — real text layer only


def _extract_text_layer(file_path: str) -> tuple[list[dict], str | None]:
    """Extract the PDF text layer.

    Returns ``(pages, error)``. ``pages`` is empty when nothing could be
    extracted; ``error`` then explains why. A placeholder string is never
    returned as page text, because callers cannot distinguish it from content.
    """
    try:
        from pypdf import PdfReader  # type: ignore[import-untyped]
    except ImportError:
        return [], "pypdf がインストールされていないためテキスト抽出できません"

    from pathlib import Path

    if not Path(file_path).exists():
        return [], "PDFファイルがサーバー上に存在しません"

    try:
        reader = PdfReader(str(file_path))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": i, "text": text})
    except Exception as exc:  # noqa: BLE001 — surface the reason to the caller
        return [], f"テキスト抽出に失敗しました: {exc}"

    if not pages:
        return [], _NO_TEXT_LAYER_MESSAGE
    return pages, None


def _to_job_response(job: OcrJob) -> OcrJobResponse:
    return OcrJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        engine=job.engine,
        language=job.language,
        enable_vertical=job.enable_vertical,
        created_at=job.created_at.isoformat() if job.created_at else "",
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        page_count=job.page_count,
        error=job.error,
    )


def _load_visible_job(db: Session, job_id: str, current_user: User) -> OcrJob:
    """Load a job, enforcing the visibility of the document it belongs to."""
    job = db.query(OcrJob).filter(OcrJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OCR job not found"
        )
    document = db.query(Document).filter(Document.id == job.document_id).first()
    # Raises 404 when the document is not visible to this user, so a leaked job
    # id cannot be used to read another organization's document text.
    assert_document_visible(document, current_user)
    return job


@router.post(
    "/process", response_model=OcrJobResponse, status_code=status.HTTP_202_ACCEPTED
)
def start_ocr(
    body: OcrJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Extract the text layer of a document and persist the job.

    Returns HTTP 202 with the job id; extraction is performed synchronously (the
    job is already finished when the response is returned).
    """
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    assert_document_visible(doc, current_user)
    if not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Document file has been deleted (GDPR erasure)",
        )

    now = datetime.now(timezone.utc)
    pages, error = _extract_text_layer(doc.file_path)
    completed_at = datetime.now(timezone.utc)

    if pages:
        job_status = OCR_STATUS_COMPLETED
    elif error == _NO_TEXT_LAYER_MESSAGE:
        job_status = OCR_STATUS_UNSUPPORTED
    else:
        job_status = OCR_STATUS_FAILED

    job = OcrJob(
        document_id=doc.id,
        requested_by=current_user.id,
        status=job_status,
        engine=OCR_ENGINE_TEXT_LAYER,
        language=body.language,
        enable_vertical=body.enable_vertical,
        page_count=len(pages),
        error=error,
        pages=pages or None,
        created_at=now,
        completed_at=completed_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_job_response(job)


@router.get("/jobs/{job_id}", response_model=OcrJobResponse)
def get_ocr_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrJobResponse:
    """Poll an extraction job. Only jobs for visible documents are returned."""
    return _to_job_response(_load_visible_job(db, job_id, current_user))


@router.get("/jobs/{job_id}/result", response_model=OcrResultResponse)
def get_ocr_result(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrResultResponse:
    """Return the extracted text pages for a visible document's job."""
    job = _load_visible_job(db, job_id, current_user)
    if job.status == OCR_STATUS_FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"OCR job failed: {job.error}",
        )
    return OcrResultResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        engine=job.engine,
        pages=job.pages or [],
    )
