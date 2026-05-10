from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.user import User, Project
from auth.dependencies import get_current_user, require_manager
from api.schemas import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "admin":
        return db.query(Project).all()
    return current_user.projects


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    if db.query(Project).filter(Project.code == body.code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Project code already exists"
        )

    project = Project(
        name=body.name,
        code=body.code,
        description=body.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


@router.post("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user not in project.members:
        project.members.append(user)
        db.commit()


@router.delete(
    "/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    project_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user and user in project.members:
        project.members.remove(user)
        db.commit()
