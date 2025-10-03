"""Event tracking models."""

import enum

from sqlalchemy import JSON, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from newsauto.models.base import BaseModel


class EventType(str, enum.Enum):
    """Event type enum."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    OPEN = "open"
    CLICK = "click"
    BOUNCE = "bounce"
    COMPLAINT = "complaint"
    FORWARD = "forward"


class SubscriberEvent(BaseModel):
    """Subscriber event tracking model."""

    __tablename__ = "subscriber_events"

    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    edition_id = Column(Integer, ForeignKey("editions.id"))
    event_type = Column(Enum(EventType), nullable=False)
    meta_data = Column(JSON, default=dict)
    ip_address = Column(String(45))
    user_agent = Column(String(500))

    # Relationships
    subscriber = relationship("Subscriber", back_populates="events")
    edition = relationship("Edition")

    def __repr__(self):
        return f"<SubscriberEvent(id={self.id}, type={self.event_type}, subscriber_id={self.subscriber_id})>"

    @property
    def is_engagement(self) -> bool:
        """Check if event is an engagement event."""
        return self.event_type in [EventType.OPEN, EventType.CLICK, EventType.FORWARD]

    @property
    def is_negative(self) -> bool:
        """Check if event is negative."""
        return self.event_type in [
            EventType.UNSUBSCRIBE,
            EventType.BOUNCE,
            EventType.COMPLAINT,
        ]
