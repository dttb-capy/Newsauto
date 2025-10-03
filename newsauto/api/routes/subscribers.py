"""Subscriber API endpoints."""

import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from newsauto.api.routes.auth import get_current_user
from newsauto.api.routes.verification import send_verification_email
from newsauto.auth.tokens import TokenGenerator
from newsauto.core.database import get_db
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import (
    NewsletterSubscriber,
    Subscriber,
    SubscriberStatus,
)
from newsauto.models.user import User
from newsauto.models.events import SubscriberEvent, EventType

router = APIRouter()
settings = get_settings()


class SubscriberCreate(BaseModel):
    """Subscriber creation model."""

    email: EmailStr
    name: Optional[str] = None
    newsletter_ids: List[int]
    preferences: dict = {}
    segments: List[str] = []


class SubscriberUpdate(BaseModel):
    """Subscriber update model."""

    name: Optional[str] = None
    preferences: Optional[dict] = None
    segments: Optional[List[str]] = None
    status: Optional[SubscriberStatus] = None


class SubscriberResponse(BaseModel):
    """Subscriber response model."""

    id: int
    email: str
    name: Optional[str]
    status: SubscriberStatus
    preferences: dict
    segments: list
    verified_at: Optional[datetime]
    subscribed_at: datetime
    last_email_sent: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SubscriberResponse])
async def list_subscribers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    newsletter_id: Optional[int] = None,
    status: Optional[SubscriberStatus] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List subscribers."""
    query = db.query(Subscriber)

    if newsletter_id:
        # Verify newsletter ownership
        newsletter = (
            db.query(Newsletter)
            .filter(
                Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id
            )
            .first()
        )

        if not newsletter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Newsletter not found"
            )

        # Filter by newsletter
        query = query.join(NewsletterSubscriber).filter(
            NewsletterSubscriber.newsletter_id == newsletter_id,
            NewsletterSubscriber.unsubscribed_at is None,
        )

    if status:
        query = query.filter(Subscriber.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Subscriber.email.ilike(search_term)) | (Subscriber.name.ilike(search_term))
        )

    subscribers = query.offset(skip).limit(limit).all()
    return subscribers


@router.post(
    "/", response_model=SubscriberResponse, status_code=status.HTTP_201_CREATED
)
async def create_subscriber(
    subscriber_data: SubscriberCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new subscriber."""
    # Check if subscriber exists
    existing = (
        db.query(Subscriber).filter(Subscriber.email == subscriber_data.email).first()
    )

    if existing:
        # Add to new newsletters if already exists
        subscriber = existing
    else:
        # Create new subscriber
        subscriber = Subscriber(
            email=subscriber_data.email,
            name=subscriber_data.name,
            preferences=subscriber_data.preferences,
            segments=subscriber_data.segments,
            status=SubscriberStatus.PENDING,
            verification_token=secrets.token_urlsafe(32),
        )
        db.add(subscriber)
        db.flush()

    # Subscribe to newsletters
    for newsletter_id in subscriber_data.newsletter_ids:
        # Verify newsletter ownership
        newsletter = (
            db.query(Newsletter)
            .filter(
                Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id
            )
            .first()
        )

        if not newsletter:
            continue

        # Check if already subscribed
        existing_sub = (
            db.query(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.newsletter_id == newsletter_id,
                NewsletterSubscriber.subscriber_id == subscriber.id,
            )
            .first()
        )

        if not existing_sub:
            newsletter_sub = NewsletterSubscriber(
                newsletter_id=newsletter_id, subscriber_id=subscriber.id
            )
            db.add(newsletter_sub)

            # Update subscriber count
            newsletter.subscriber_count = (
                db.query(NewsletterSubscriber)
                .filter(
                    NewsletterSubscriber.newsletter_id == newsletter_id,
                    NewsletterSubscriber.unsubscribed_at is None,
                )
                .count()
            )

    db.commit()
    db.refresh(subscriber)

    # Send verification email if new subscriber
    if not existing and settings.enable_registration:
        token = TokenGenerator.generate_verification_token(subscriber.email)
        verification_url = f"{settings.frontend_url}/verify?token={token}"

        background_tasks.add_task(
            send_verification_email,
            subscriber.email,
            subscriber.name,
            verification_url
        )

        # Log event
        event = SubscriberEvent(
            subscriber_id=subscriber.id,
            event_type=EventType.VERIFICATION_SENT,
            metadata={"method": "registration"}
        )
        db.add(event)
        db.commit()

    return subscriber


@router.get("/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(
    subscriber_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscriber details."""
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber not found"
        )

    return subscriber


@router.put("/{subscriber_id}", response_model=SubscriberResponse)
async def update_subscriber(
    subscriber_id: int,
    update_data: SubscriberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update subscriber."""
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber not found"
        )

    # Update fields
    if update_data.name is not None:
        subscriber.name = update_data.name

    if update_data.preferences is not None:
        subscriber.preferences = {**subscriber.preferences, **update_data.preferences}

    if update_data.segments is not None:
        subscriber.segments = update_data.segments

    if update_data.status is not None:
        subscriber.status = update_data.status

    subscriber.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(subscriber)

    return subscriber


@router.post("/{subscriber_id}/unsubscribe")
async def unsubscribe(
    subscriber_id: int,
    newsletter_id: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Unsubscribe from newsletter(s)."""
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber not found"
        )

    if newsletter_id:
        # Unsubscribe from specific newsletter
        newsletter_sub = (
            db.query(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.subscriber_id == subscriber_id,
                NewsletterSubscriber.newsletter_id == newsletter_id,
            )
            .first()
        )

        if newsletter_sub:
            newsletter_sub.unsubscribed_at = datetime.utcnow()

            # Update newsletter subscriber count
            newsletter = (
                db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
            )
            if newsletter:
                newsletter.subscriber_count = (
                    db.query(NewsletterSubscriber)
                    .filter(
                        NewsletterSubscriber.newsletter_id == newsletter_id,
                        NewsletterSubscriber.unsubscribed_at is None,
                    )
                    .count()
                )
    else:
        # Unsubscribe from all newsletters
        subscriber.status = SubscriberStatus.UNSUBSCRIBED
        subscriber.unsubscribed_at = datetime.utcnow()
        subscriber.unsubscribe_reason = reason

        # Mark all newsletter subscriptions as unsubscribed
        newsletter_subs = (
            db.query(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.subscriber_id == subscriber_id,
                NewsletterSubscriber.unsubscribed_at is None,
            )
            .all()
        )

        for sub in newsletter_subs:
            sub.unsubscribed_at = datetime.utcnow()

    db.commit()

    return {"message": "Successfully unsubscribed"}


@router.post("/{subscriber_id}/verify")
async def verify_subscriber(
    subscriber_id: int, token: str, db: Session = Depends(get_db)
):
    """Verify subscriber email."""
    subscriber = (
        db.query(Subscriber)
        .filter(Subscriber.id == subscriber_id, Subscriber.verification_token == token)
        .first()
    )

    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    subscriber.status = SubscriberStatus.ACTIVE
    subscriber.verified_at = datetime.utcnow()
    subscriber.verification_token = None

    db.commit()

    return {"message": "Email verified successfully"}
