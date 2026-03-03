"""
Layer 3.3 & 3.4 — Workflow Proposal & Approval routes.

Provides:
  - POST /life-events/propose-workflow (Read-only generation)
  - POST /life-events/approve-workflow (DB persistence)

Mounted under the /life-events prefix in main.py.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.schemas.workflow_approval_schema import (
    WorkflowApprovalRequest,
    WorkflowApprovalResponse,
)
from backend.schemas.workflow_schema import (
    WorkflowProposalRequest,
    WorkflowProposalResponse,
)
from backend.services.workflow_approval_service import approve_workflow
from backend.services.workflow_generation_service import propose_workflow

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "/propose-workflow",
    response_model=WorkflowProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Propose a task workflow for one or more life events (RAG + AI)",
    description=(
        "Retrieves relevant requirements from the knowledge base via semantic search, "
        "then uses Gemini to generate an ordered task workflow grounded exclusively "
        "on the retrieved content. No data is saved to the database.\n\n"
        "If retrieved knowledge is insufficient, the response will contain "
        "`success: false` and an `error` message rather than a 5xx."
    ),
)
def propose_life_event_workflow(
    body: WorkflowProposalRequest,
    db: Session = Depends(get_db),
) -> WorkflowProposalResponse:
    """
    POST /life-events/propose-workflow

    - Runs RAG retrieval for each life_event_type.
    - Passes retrieved chunks + context to Gemini (strictly grounded).
    - Returns a validated Pydantic workflow response.
    - On insufficient knowledge: returns 200 with success=False + error message.
    - On infrastructure failure: returns 503.
    """
    try:
        return propose_workflow(
            db=db,
            life_event_types=body.life_event_types,
            location=body.location,
            timeline=body.timeline,
            top_k=body.top_k,
        )
    except ValueError as exc:
        # Empty KB or no entries for requested types
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        # Embedding or LLM infrastructure failure
        logger.error("Workflow generation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# POST /life-events/approve-workflow
# ---------------------------------------------------------------------------

@router.post(
    "/approve-workflow",
    response_model=WorkflowApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Persist an approved workflow proposal as Task records",
    description=(
        "Converts an approved Layer 3.3 workflow proposal into real Task records "
        "in the database. No LLM is called — only persists what the user submits. "
        "Duplicate tasks (same title under the same life event) are silently skipped, "
        "making this endpoint safe to call multiple times (idempotent)."
    ),
)
def approve_life_event_workflow(
    body: WorkflowApprovalRequest,
    db: Session = Depends(get_db),
) -> WorkflowApprovalResponse:
    """
    POST /life-events/approve-workflow

    - Validates life_event_id exists (404 if not).
    - Computes due_date = now_utc + due_offset_days for each task/subtask.
    - Skips tasks whose title already exists under this life_event_id.
    - Commits atomically; rolls back on any DB failure.
    - Returns created task IDs and skipped duplicate titles.
    """
    try:
        return approve_workflow(db=db, request=body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Workflow approval DB error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
