"""Electronic delivery (電子納品) ZIP generation API.

Provides:
  GET  /projects/{project_id}/electronic-delivery/check   — readiness check
  POST /projects/{project_id}/electronic-delivery         — generate & download ZIP
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.schemas import ElectronicDeliveryCheckResponse
from auth.dependencies import get_current_user, require_manager
from database import get_db
from models.document import Document
from models.user import Project, User
from services import electronic_delivery_service
from services.access_control import assert_project_visible

router = APIRouter(prefix="/projects", tags=["ElectronicDelivery"])


def _get_project_or_404(project_id: str, db: Session, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    return assert_project_visible(project, user)


@router.get(
    "/{project_id}/electronic-delivery/check",
    response_model=ElectronicDeliveryCheckResponse,
)
def check_delivery_readiness(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return readiness status for electronic delivery packaging."""
    project = _get_project_or_404(project_id, db, current_user)
    documents = db.query(Document).filter(Document.project_id == project_id).all()
    result = electronic_delivery_service.check_delivery_readiness(project, documents)
    return result


@router.post("/{project_id}/electronic-delivery", status_code=status.HTTP_200_OK)
def generate_delivery_zip(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Generate and stream a MLIT-conformant electronic delivery ZIP package."""
    project = _get_project_or_404(project_id, db, current_user)
    documents = db.query(Document).filter(Document.project_id == project_id).all()

    zip_bytes = electronic_delivery_service.generate_delivery_zip(project, documents)

    from datetime import datetime, timezone

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    from services.electronic_delivery_service import _sanitize_code

    proj_code = _sanitize_code(project.code)
    filename = f"{proj_code}_{date_str}.zip"

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
