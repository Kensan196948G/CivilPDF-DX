from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models.user import User
from models.document import Document, DocumentStatus, ApprovalWorkflow, ApprovalStep
from auth.dependencies import get_current_user
from api.schemas import WorkflowCreate, WorkflowResponse, ApprovalDecision

router = APIRouter(prefix="/workflows", tags=["Approval Workflows"])


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == body.document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if (
        db.query(ApprovalWorkflow)
        .filter(ApprovalWorkflow.document_id == body.document_id)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow already exists for this document",
        )

    if not body.approver_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one approver is required",
        )

    workflow = ApprovalWorkflow(document_id=body.document_id, status="in_progress")
    db.add(workflow)
    db.flush()

    for i, approver_id in enumerate(body.approver_ids):
        approver = db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approver {approver_id} not found",
            )
        step = ApprovalStep(
            workflow_id=workflow.id,
            approver_id=approver_id,
            order=i + 1,
            status="pending" if i > 0 else "pending",
        )
        db.add(step)

    doc.status = DocumentStatus.PENDING_REVIEW
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workflow = (
        db.query(ApprovalWorkflow).filter(ApprovalWorkflow.id == workflow_id).first()
    )
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


@router.post("/{workflow_id}/steps/{step_id}/decide", response_model=WorkflowResponse)
def decide_step(
    workflow_id: str,
    step_id: str,
    body: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    step = (
        db.query(ApprovalStep)
        .filter(
            ApprovalStep.id == step_id,
            ApprovalStep.workflow_id == workflow_id,
        )
        .first()
    )
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Step not found"
        )
    if step.approver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the approver for this step",
        )
    if step.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Step already decided"
        )

    step.status = body.decision if body.decision == "approved" else "rejected"
    # normalize: "approve" -> "approved", "reject" -> "rejected"
    step.status = "approved" if body.decision == "approve" else "rejected"
    step.comment = body.comment
    step.decided_at = datetime.now(timezone.utc)

    workflow = step.workflow
    document = workflow.document

    if body.decision == "reject":
        workflow.status = "rejected"
        workflow.completed_at = datetime.now(timezone.utc)
        document.status = DocumentStatus.REJECTED
    else:
        # Check if all steps approved
        all_steps = (
            db.query(ApprovalStep).filter(ApprovalStep.workflow_id == workflow_id).all()
        )
        if all(s.status == "approved" for s in all_steps):
            workflow.status = "approved"
            workflow.completed_at = datetime.now(timezone.utc)
            document.status = DocumentStatus.APPROVED
        else:
            # Activate next step
            next_step = (
                db.query(ApprovalStep)
                .filter(
                    ApprovalStep.workflow_id == workflow_id,
                    ApprovalStep.order == step.order + 1,
                )
                .first()
            )
            if next_step:
                next_step.status = "pending"

    db.commit()
    db.refresh(workflow)
    return workflow
