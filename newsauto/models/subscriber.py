"""Subscriber models."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from newsauto.models.base import BaseModel


class SubscriberStatus(str, enum.Enum):
    """Subscriber status enum."""

    PENDING = "pending"
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"


class Subscriber(BaseModel):
    """Subscriber model."""

    __tablename__ = "subscribers"

    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255))
    preferences = Column(JSON, default=dict)
    segments = Column(JSON, default=list)
    status = Column(
        Enum(SubscriberStatus), default=SubscriberStatus.PENDING, nullable=False
    )
    verification_token = Column(String(255))
    verified_at = Column(DateTime)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    unsubscribed_at = Column(DateTime)
    unsubscribe_reason = Column(String(255))
    last_email_sent = Column(DateTime)
    bounce_count = Column(Integer, default=0)

    # Relationships
    newsletters = relationship(
        "NewsletterSubscriber",
        back_populates="subscriber",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "SubscriberEvent", back_populates="subscriber", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Subscriber(id={self.id}, email='{self.email}', status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if subscriber is active."""
        return self.status == SubscriberStatus.ACTIVE

    @property
    def topics(self) -> list:
        """Get subscriber topic preferences."""
        return self.preferences.get("topics", [])

    def can_receive_email(self) -> bool:
        """Check if subscriber can receive emails."""
        return self.status == SubscriberStatus.ACTIVE and self.verified_at is not None


class NewsletterSubscriber(BaseModel):
    """Many-to-many relationship between newsletters and subscribers."""

    __tablename__ = "newsletter_subscribers"
    __table_args__ = (
        UniqueConstraint(
            "newsletter_id", "subscriber_id", name="uq_newsletter_subscriber"
        ),
    )

    newsletter_id = Column(Integer, ForeignKey("newsletters.id"), nullable=False)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    unsubscribed_at = Column(DateTime)
    preferences = Column(JSON, default=dict)

    # Relationships
    newsletter = relationship("Newsletter", back_populates="subscribers")
    subscriber = relationship("Subscriber", back_populates="newsletters")

    def __repr__(self):
        return f"<NewsletterSubscriber(newsletter_id={self.newsletter_id}, subscriber_id={self.subscriber_id})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.unsubscribed_at is None
