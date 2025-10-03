"""API route modules."""

from newsauto.api.routes import (
    analytics,
    auth,
    content,
    editions,
    health,
    newsletters,
    subscribers,
)

__all__ = [
    "auth",
    "newsletters",
    "subscribers",
    "content",
    "editions",
    "analytics",
    "health",
]
