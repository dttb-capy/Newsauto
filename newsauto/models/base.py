"""Base model for all database models."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer

from newsauto.core.database import Base


class BaseModel(Base):
    """Base model with common fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
