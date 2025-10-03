"""Newsletter API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from newsauto.api.routes.auth import get_current_user
from newsauto.core.database import get_db
from newsauto.models.content import ContentSource, ContentSourceType
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.user import User

router = APIRouter()


class NewsletterCreate(BaseModel):
    """Newsletter creation model."""

    name: str
    niche: Optional[str] = None
    description: Optional[str] = None
    settings: dict = {}


class NewsletterUpdate(BaseModel):
    """Newsletter update model."""

    name: Optional[str] = None
    niche: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[dict] = None
    status: Optional[NewsletterStatus] = None


class NewsletterResponse(BaseModel):
    """Newsletter response model."""

    id: int
    name: str
    niche: Optional[str]
    description: Optional[str]
    status: NewsletterStatus
    subscriber_count: int
    settings: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentSourceCreate(BaseModel):
    """Content source creation model."""

    name: str
    type: ContentSourceType
    url: Optional[str] = None
    config: dict = {}
    active: bool = True
    fetch_frequency_minutes: int = 60


class ContentSourceResponse(BaseModel):
    """Content source response model."""

    id: int
    name: str
    type: ContentSourceType
    url: Optional[str]
    config: dict
    active: bool
    last_fetched: Optional[datetime]
    fetch_frequency_minutes: int
    error_count: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NewsletterResponse])
async def list_newsletters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[NewsletterStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List newsletters for current user."""
    query = db.query(Newsletter).filter(Newsletter.user_id == current_user.id)

    if status:
        query = query.filter(Newsletter.status == status)

    newsletters = query.offset(skip).limit(limit).all()
    return newsletters


@router.post(
    "/", response_model=NewsletterResponse, status_code=status.HTTP_201_CREATED
)
async def create_newsletter(
    newsletter_data: NewsletterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new newsletter."""
    # Check name uniqueness
    existing = (
        db.query(Newsletter).filter(Newsletter.name == newsletter_data.name).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Newsletter name already exists",
        )

    # Check user limit
    user_newsletters = (
        db.query(Newsletter).filter(Newsletter.user_id == current_user.id).count()
    )

    from newsauto.core.config import get_settings

    settings = get_settings()

    if user_newsletters >= settings.max_newsletters_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum newsletters limit ({settings.max_newsletters_per_user}) reached",
        )

    # Create newsletter
    newsletter = Newsletter(
        name=newsletter_data.name,
        niche=newsletter_data.niche,
        description=newsletter_data.description,
        settings=newsletter_data.settings,
        user_id=current_user.id,
        status=NewsletterStatus.DRAFT,
    )

    db.add(newsletter)
    db.commit()
    db.refresh(newsletter)

    return newsletter


@router.get("/{newsletter_id}", response_model=NewsletterResponse)
async def get_newsletter(
    newsletter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get newsletter details."""
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    return newsletter


@router.put("/{newsletter_id}", response_model=NewsletterResponse)
async def update_newsletter(
    newsletter_id: int,
    update_data: NewsletterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update newsletter."""
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    # Update fields
    if update_data.name is not None:
        # Check name uniqueness
        existing = (
            db.query(Newsletter)
            .filter(Newsletter.name == update_data.name, Newsletter.id != newsletter_id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Newsletter name already exists",
            )
        newsletter.name = update_data.name

    if update_data.niche is not None:
        newsletter.niche = update_data.niche

    if update_data.description is not None:
        newsletter.description = update_data.description

    if update_data.settings is not None:
        newsletter.settings = {**newsletter.settings, **update_data.settings}

    if update_data.status is not None:
        newsletter.status = update_data.status

    newsletter.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(newsletter)

    return newsletter


@router.delete("/{newsletter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_newsletter(
    newsletter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete newsletter."""
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    db.delete(newsletter)
    db.commit()


# Content Source Management


@router.get("/{newsletter_id}/sources", response_model=List[ContentSourceResponse])
async def list_content_sources(
    newsletter_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List content sources for a newsletter."""
    # Verify newsletter ownership
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    sources = (
        db.query(ContentSource)
        .filter(ContentSource.newsletter_id == newsletter_id)
        .all()
    )

    return sources


@router.post(
    "/{newsletter_id}/sources",
    response_model=ContentSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_source(
    newsletter_id: int,
    source_data: ContentSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add content source to newsletter."""
    # Verify newsletter ownership
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    # Create content source
    source = ContentSource(
        name=source_data.name,
        type=source_data.type,
        url=source_data.url,
        config=source_data.config,
        active=source_data.active,
        fetch_frequency_minutes=source_data.fetch_frequency_minutes,
        newsletter_id=newsletter_id,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    return source


@router.delete(
    "/{newsletter_id}/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_content_source(
    newsletter_id: int,
    source_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete content source."""
    # Verify newsletter ownership
    newsletter = (
        db.query(Newsletter)
        .filter(Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id)
        .first()
    )

    if not newsletter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
        )

    source = (
        db.query(ContentSource)
        .filter(
            ContentSource.id == source_id, ContentSource.newsletter_id == newsletter_id
        )
        .first()
    )

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content source not found"
        )

    db.delete(source)
    db.commit()
