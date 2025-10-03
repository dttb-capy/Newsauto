"""Cache model for LLM responses."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from newsauto.models.base import BaseModel


class CacheEntry(BaseModel):
    """Cache entry model for LLM responses."""

    __tablename__ = "cache_entries"

    cache_key = Column(String(64), unique=True, nullable=False)
    content_hash = Column(String(64))
    model = Column(String(100))
    response = Column(Text)
    meta_data = Column(JSON, default=dict)
    expires_at = Column(DateTime)
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)

    def __repr__(self):
        return f"<CacheEntry(key='{self.cache_key[:8]}...', model='{self.model}', hits={self.hit_count})>"

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def increment_hit(self):
        """Increment hit count and update last accessed time."""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()
