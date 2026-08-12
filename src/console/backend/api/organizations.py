from fastapi import APIRouter, Depends, HTTPException, status
import json
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.user import User
from models.organization import Organization
from auth.dependencies import get_current_user
from api.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from services.audit_chain_service import create_chained_audit_log

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def _build_path(parent: Organization | None) -> str:
    if parent is None:
        return "/"
    return parent.path.rstrip("/") + f"/{parent.id}"


def _require_admin(current_user: User) -> None:
    if current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")


@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all active organizations (flat list; children populated by Pydantic recursion)."""
    return db.query(Organization).filter(Organization.is_active.is_(True)).all()


@router.get("/tree", response_model=List[OrganizationResponse])
def organization_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return root organizations with nested children (tree view)."""
    roots = (
        db.query(Organization)
        .filter(Organization.parent_id.is_(None), Organization.is_active.is_(True))
        .all()
    )
    return roots


@router.post(
    "/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
def create_organization(
    body: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    if db.query(Organization).filter(Organization.code == body.code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization code '{body.code}' already exists",
        )

    parent = None
    if body.parent_id:
        parent = (
            db.query(Organization).filter(Organization.id == body.parent_id).first()
        )
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent organization not found",
            )

    org = Organization(
        name=body.name,
        code=body.code,
        org_type=body.org_type,
        parent_id=body.parent_id,
        path=_build_path(parent),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="organization.created",
        resource_type="organization",
        resource_id=org.id,
        detail=json.dumps(
            {"name": org.name, "code": org.code, "org_type": org.org_type.value}
        ),
        ip_address=None,
    )
    return org


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    return org


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: str,
    body: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="organization.updated",
        resource_type="organization",
        resource_id=org_id,
        detail=json.dumps(body.model_dump(exclude_none=True)),
        ip_address=None,
    )
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete: set is_active=False."""
    _require_admin(current_user)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    if org.children:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete organization with active children",
        )

    org.is_active = False
    db.commit()
    create_chained_audit_log(
        db,
        user_id=current_user.id,
        action="organization.deleted",
        resource_type="organization",
        resource_id=org_id,
        detail=json.dumps({"name": org.name, "code": org.code}),
        ip_address=None,
    )


@router.get("/{org_id}/members", response_model=List[dict])
def list_members(
    org_id: str,
    include_subtree: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List users belonging to this organization (or whole subtree)."""
    _require_admin(current_user)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    from models.user import User as UserModel

    if include_subtree:
        # All orgs whose path starts with this org's subtree prefix
        subtree_prefix = org.path.rstrip("/") + f"/{org_id}"
        orgs = (
            db.query(Organization)
            .filter(
                (Organization.id == org_id)
                | Organization.path.like(f"{subtree_prefix}%")
            )
            .all()
        )
        org_ids = [o.id for o in orgs]
        users = db.query(UserModel).filter(UserModel.organization_id.in_(org_ids)).all()
    else:
        users = db.query(UserModel).filter(UserModel.organization_id == org_id).all()

    return [
        {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role.value}
        for u in users
    ]
