"""Edition models for newsletter editions."""

import enum

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


class EditionStatus(str, enum.Enum):
    """Edition status enum."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class Edition(BaseModel):
    """Newsletter edition model."""

    __tablename__ = "editions"

    newsletter_id = Column(Integer, ForeignKey("newsletters.id"), nullable=False)
    edition_number = Column(Integer)
    subject = Column(String(500))
    preheader = Column(String(255))
    content = Column(JSON, nullable=False)
    template_data = Column(JSON, default=dict)
    status = Column(Enum(EditionStatus), default=EditionStatus.DRAFT, nullable=False)
    test_mode = Column(Boolean, default=False)
    scheduled_for = Column(DateTime)
    sent_at = Column(DateTime)

    # Relationships
    newsletter = relationship("Newsletter", back_populates="editions")
    content_items = relationship(
        "EditionContent", back_populates="edition", cascade="all, delete-orphan"
    )
    stats = relationship(
        "EditionStats",
        uselist=False,
        back_populates="edition",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Edition(id={self.id}, newsletter_id={self.newsletter_id}, status={self.status})>"

    @property
    def is_sent(self) -> bool:
        """Check if edition has been sent."""
        return self.status == EditionStatus.SENT

    @property
    def article_count(self) -> int:
        """Get number of articles in edition."""
        if isinstance(self.content, dict):
            sections = self.content.get("sections", [])
            return sum(len(section.get("items", [])) for section in sections)
        return 0


class EditionContent(BaseModel):
    """Link between editions and content items."""

    __tablename__ = "edition_content"

    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False)
    content_id = Column(Integer, ForeignKey("content_items.id"), nullable=False)
    position = Column(Integer, nullable=False)
    section = Column(String(100))
    custom_summary = Column(Text)

    # Relationships
    edition = relationship("Edition", back_populates="content_items")
    content = relationship("ContentItem", back_populates="editions")

    def __repr__(self):
        return f"<EditionContent(edition_id={self.edition_id}, content_id={self.content_id}, position={self.position})>"


class EditionStats(BaseModel):
    """Edition statistics model."""

    __tablename__ = "edition_stats"

    edition_id = Column(Integer, ForeignKey("editions.id"), nullable=False, unique=True)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    unsubscribed_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    complained_count = Column(Integer, default=0)
    forwarded_count = Column(Integer, default=0)
    open_rate = Column(Float)
    click_rate = Column(Float)

    # Relationships
    edition = relationship("Edition", back_populates="stats")

    def __repr__(self):
        return f"<EditionStats(edition_id={self.edition_id}, open_rate={self.open_rate}, click_rate={self.click_rate})>"

    def calculate_rates(self):
        """Calculate open and click rates."""
        if self.sent_count > 0:
            self.open_rate = (self.opened_count / self.sent_count) * 100
            self.click_rate = (self.clicked_count / self.sent_count) * 100
        else:
            self.open_rate = 0.0
            self.click_rate = 0.0
