"""Content models for sources and items."""

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from newsauto.models.base import BaseModel


class ContentSourceType(str, enum.Enum):
    """Content source type enum."""

    RSS = "rss"
    REDDIT = "reddit"
    HACKERNEWS = "hackernews"
    WEB = "web"
    API = "api"
    GITHUB = "github"
    DEVTO = "devto"
    ARXIV = "arxiv"


class ContentSource(BaseModel):
    """Content source model."""

    __tablename__ = "content_sources"

    name = Column(String(255), nullable=False)
    type = Column(Enum(ContentSourceType), nullable=False)
    url = Column(String(500))
    config = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    last_fetched = Column(DateTime)
    fetch_frequency_minutes = Column(Integer, default=60)
    error_count = Column(Integer, default=0)
    newsletter_id = Column(Integer, ForeignKey("newsletters.id"))

    # Relationships
    newsletter = relationship("Newsletter", back_populates="content_sources")
    content_items = relationship(
        "ContentItem", back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ContentSource(id={self.id}, name='{self.name}', type={self.type})>"

    @property
    def is_active(self) -> bool:
        """Check if source is active."""
        return self.active and self.error_count < 5

    @property
    def needs_fetch(self) -> bool:
        """Check if source needs to be fetched."""
        if not self.last_fetched:
            return True

        from datetime import timedelta

        next_fetch = self.last_fetched + timedelta(minutes=self.fetch_frequency_minutes)
        return datetime.utcnow() >= next_fetch


class ContentItem(BaseModel):
    """Content item model."""

    __tablename__ = "content_items"

    source_id = Column(Integer, ForeignKey("content_sources.id"), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    content = Column(Text)
    summary = Column(Text)
    key_points = Column(JSON, default=list)
    score = Column(Float, default=0.0)
    content_hash = Column(String(64))
    meta_data = Column(JSON, default=dict)
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    llm_model = Column(String(100))
    processing_time_ms = Column(Integer)

    # Relationships
    source = relationship("ContentSource", back_populates="content_items")
    editions = relationship(
        "EditionContent", back_populates="content", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ContentItem(id={self.id}, title='{self.title[:50]}...', score={self.score})>"

    @property
    def is_processed(self) -> bool:
        """Check if content has been processed."""
        return self.processed_at is not None

    @property
    def word_count(self) -> int:
        """Get word count from metadata or calculate."""
        if "word_count" in self.meta_data:
            return self.meta_data["word_count"]
        if self.content:
            return len(self.content.split())
        return 0

    @property
    def reading_time_minutes(self) -> int:
        """Estimate reading time in minutes."""
        # Average reading speed: 200 words per minute
        return max(1, self.word_count // 200)
