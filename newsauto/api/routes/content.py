"""Content API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from newsauto.api.routes.auth import get_current_user
from newsauto.core.database import get_db
from newsauto.models.content import ContentItem
from newsauto.models.user import User
from newsauto.scrapers.aggregator import ContentAggregator

router = APIRouter()


class ContentResponse(BaseModel):
    """Content response model."""

    id: int
    url: str
    title: str
    author: Optional[str]
    summary: Optional[str]
    score: float
    published_at: Optional[datetime]
    fetched_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class FetchRequest(BaseModel):
    """Content fetch request."""

    newsletter_id: Optional[int] = None
    sources: List[str] = []
    limit: int = 100


@router.get("/", response_model=List[ContentResponse])
async def list_content(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0, ge=0, le=100),
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent content items."""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(hours=hours)

    content = (
        db.query(ContentItem)
        .filter(ContentItem.fetched_at >= since, ContentItem.score >= min_score)
        .order_by(ContentItem.score.desc(), ContentItem.published_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return content


@router.post("/fetch")
async def fetch_content(
    request: FetchRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger content fetching."""
    aggregator = ContentAggregator(db)

    # Run in background
    background_tasks.add_task(
        aggregator.fetch_and_process,
        newsletter_id=request.newsletter_id,
        process_with_llm=True,
    )

    return {"message": "Content fetching started", "task": "processing"}


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get content item details."""
    content = db.query(ContentItem).filter(ContentItem.id == content_id).first()

    if not content:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
        )

    return content
