"""Newsletter model."""

import enum

from sqlalchemy import JSON, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from newsauto.models.base import BaseModel


class NewsletterStatus(str, enum.Enum):
    """Newsletter status enum."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Newsletter(BaseModel):
    """Newsletter model."""

    __tablename__ = "newsletters"

    name = Column(String(255), nullable=False, unique=True)
    niche = Column(String(100))
    description = Column(Text)
    template_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    settings = Column(JSON, default=dict)
    status = Column(
        Enum(NewsletterStatus), default=NewsletterStatus.DRAFT, nullable=False
    )
    subscriber_count = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="newsletters")
    subscribers = relationship(
        "NewsletterSubscriber",
        back_populates="newsletter",
        cascade="all, delete-orphan",
    )
    editions = relationship(
        "Edition", back_populates="newsletter", cascade="all, delete-orphan"
    )
    content_sources = relationship(
        "ContentSource", back_populates="newsletter", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Newsletter(id={self.id}, name='{self.name}', status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if newsletter is active."""
        return self.status == NewsletterStatus.ACTIVE

    @property
    def frequency(self) -> str:
        """Get newsletter frequency from settings."""
        return self.settings.get("frequency", "weekly")

    @property
    def send_time(self) -> str:
        """Get newsletter send time from settings."""
        return self.settings.get("send_time", "08:00")

    @property
    def max_articles(self) -> int:
        """Get maximum articles per edition from settings."""
        return self.settings.get("max_articles", 10)
