"""Edition API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from newsauto.api.routes.auth import get_current_user
from newsauto.core.database import get_db
from newsauto.models.edition import Edition, EditionStatus
from newsauto.models.newsletter import Newsletter
from newsauto.models.user import User

router = APIRouter()


class GenerateRequest(BaseModel):
    """Edition generation request."""

    newsletter_id: int
    test_mode: bool = False
    max_articles: int = 10
    min_score: float = 50.0


class EditionResponse(BaseModel):
    """Edition response model."""

    id: int
    newsletter_id: int
    edition_number: Optional[int]
    subject: Optional[str]
    status: EditionStatus
    test_mode: bool
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/generate", response_model=EditionResponse)
async def generate_edition(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate newsletter edition."""
    # Verify newsletter ownership
    newsletter = (
        db.query(Newsletter)
        .filter(
            Newsletter.id == request.newsletter_id,
            Newsletter.user_id == current_user.id,
        )
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    # Create edition
    edition = Edition(
        newsletter_id=newsletter.id,
        status=EditionStatus.DRAFT,
        test_mode=request.test_mode,
        content={"sections": []},  # Will be populated by generator
    )

    db.add(edition)
    db.commit()
    db.refresh(edition)

    # TODO: Add background task for generation

    return edition


@router.get("/{edition_id}/preview")
async def preview_edition(
    edition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get edition preview."""
    edition = (
        db.query(Edition)
        .join(Newsletter)
        .filter(Edition.id == edition_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )

    # TODO: Render HTML preview
    return {
        "id": edition.id,
        "html": "<h1>Newsletter Preview</h1>",
        "subject": edition.subject or "Newsletter",
    }


@router.post("/{edition_id}/send")
async def send_edition(
    edition_id: int,
    background_tasks: BackgroundTasks,
    test_email: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send newsletter edition."""
    edition = (
        db.query(Edition)
        .join(Newsletter)
        .filter(Edition.id == edition_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not edition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Edition not found"
        )

    if edition.status == EditionStatus.SENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Edition already sent"
        )

    # TODO: Add background task for sending

    return {
        "message": "Edition sending started",
        "edition_id": edition.id,
        "test_mode": bool(test_email),
    }
