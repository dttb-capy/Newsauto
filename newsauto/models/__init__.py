"""Database models for Newsauto."""

from newsauto.models.cache import CacheEntry
from newsauto.models.content import ContentItem, ContentSource
from newsauto.models.edition import Edition, EditionContent, EditionStats
from newsauto.models.events import SubscriberEvent
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import NewsletterSubscriber, Subscriber
from newsauto.models.user import APIKey, User

# List all models for easy import
all_models = [
    Newsletter,
    Subscriber,
    NewsletterSubscriber,
    ContentSource,
    ContentItem,
    Edition,
    EditionContent,
    EditionStats,
    User,
    APIKey,
    SubscriberEvent,
    CacheEntry,
]

__all__ = [
    "Newsletter",
    "Subscriber",
    "NewsletterSubscriber",
    "ContentSource",
    "ContentItem",
    "Edition",
    "EditionContent",
    "EditionStats",
    "User",
    "APIKey",
    "SubscriberEvent",
    "CacheEntry",
]
