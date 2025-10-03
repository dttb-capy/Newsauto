"""User and authentication models."""

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from newsauto.models.base import BaseModel


class UserRole(str, enum.Enum):
    """User role enum."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(BaseModel):
    """User model for admin/editors."""

    __tablename__ = "users"

    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.EDITOR, nullable=False)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, default=dict)
    last_login = Column(DateTime)

    # Relationships
    newsletters = relationship(
        "Newsletter", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    @property
    def can_edit(self) -> bool:
        """Check if user can edit content."""
        return self.role in [UserRole.ADMIN, UserRole.EDITOR]

    def set_password(self, password: str) -> None:
        """Set password hash."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        """Check password against hash."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.password_hash)


class APIKey(BaseModel):
    """API key model for external integrations."""

    __tablename__ = "api_keys"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    name = Column(String(255))
    permissions = Column(JSON, default=list)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if not self.expires_at:
            return False
        from datetime import datetime

        return datetime.utcnow() > self.expires_at

    def has_permission(self, permission: str) -> bool:
        """Check if API key has specific permission."""
        return permission in self.permissions
