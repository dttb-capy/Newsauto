"""Personalization engine for newsletter content."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from newsauto.models.content import ContentItem
from newsauto.models.events import EventType, SubscriberEvent
from newsauto.models.subscriber import Subscriber

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """Engine for personalizing newsletter content."""

    def __init__(self, db: Session):
        """Initialize personalization engine.

        Args:
            db: Database session
        """
        self.db = db

    def personalize_for_subscriber(
        self, subscriber: Subscriber, content: List[ContentItem], newsletter_id: int
    ) -> Dict[str, Any]:
        """Personalize content for specific subscriber.

        Args:
            subscriber: Subscriber object
            content: List of content items
            newsletter_id: Newsletter ID

        Returns:
            Personalized content and metadata
        """
        # Get subscriber preferences
        preferences = subscriber.preferences or {}
        segments = subscriber.segments or []

        # Get engagement history
        engagement = self.get_engagement_history(subscriber.id, newsletter_id)

        # Filter and rank content
        personalized_content = self.filter_content(
            content, preferences, segments, engagement
        )

        # Score and sort content
        scored_content = self.score_content(
            personalized_content, preferences, engagement
        )

        # Build personalized sections
        sections = self.build_sections(
            scored_content, preferences.get("max_articles", 10)
        )

        return {
            "subscriber": {
                "email": subscriber.email,
                "name": subscriber.name,
                "preferences": preferences,
                "segments": segments,
            },
            "sections": sections,
            "personalization_metadata": {
                "engagement_score": engagement.get("score", 0),
                "last_open": engagement.get("last_open"),
                "preferred_topics": self.get_preferred_topics(engagement),
                "optimal_send_time": self.get_optimal_send_time(subscriber.id),
            },
        }

    def get_engagement_history(
        self, subscriber_id: int, newsletter_id: int, days: int = 90
    ) -> Dict[str, Any]:
        """Get subscriber engagement history.

        Args:
            subscriber_id: Subscriber ID
            newsletter_id: Newsletter ID
            days: Number of days to look back

        Returns:
            Engagement metrics
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Get event counts
        events = (
            self.db.query(
                SubscriberEvent.event_type,
                func.count(SubscriberEvent.id).label("count"),
            )
            .filter(
                SubscriberEvent.subscriber_id == subscriber_id,
                SubscriberEvent.created_at >= since,
            )
            .group_by(SubscriberEvent.event_type)
            .all()
        )

        event_counts = {event.event_type: event.count for event in events}

        # Get last open
        last_open = (
            self.db.query(SubscriberEvent)
            .filter(
                SubscriberEvent.subscriber_id == subscriber_id,
                SubscriberEvent.event_type == EventType.OPEN,
            )
            .order_by(SubscriberEvent.created_at.desc())
            .first()
        )

        # Get clicked topics
        clicked_events = (
            self.db.query(SubscriberEvent)
            .filter(
                SubscriberEvent.subscriber_id == subscriber_id,
                SubscriberEvent.event_type == EventType.CLICK,
            )
            .all()
        )

        clicked_topics = {}
        for event in clicked_events:
            if event.meta_data and "topic" in event.meta_data:
                topic = event.meta_data["topic"]
                clicked_topics[topic] = clicked_topics.get(topic, 0) + 1

        # Calculate engagement score
        opens = event_counts.get(EventType.OPEN, 0)
        clicks = event_counts.get(EventType.CLICK, 0)
        engagement_score = (opens * 1 + clicks * 3) / max(days / 7, 1)

        return {
            "event_counts": event_counts,
            "last_open": last_open.created_at if last_open else None,
            "clicked_topics": clicked_topics,
            "score": engagement_score,
        }

    def filter_content(
        self,
        content: List[ContentItem],
        preferences: Dict[str, Any],
        segments: List[str],
        engagement: Dict[str, Any],
    ) -> List[ContentItem]:
        """Filter content based on preferences and segments.

        Args:
            content: List of content items
            preferences: User preferences
            segments: User segments
            engagement: Engagement history

        Returns:
            Filtered content list
        """
        filtered = []

        # Get preference filters
        blocked_keywords = preferences.get("blocked_keywords", [])
        # preferred_keywords = preferences.get("preferred_keywords", [])  # TODO: implement preference scoring
        min_score = preferences.get("min_content_score", 50)

        for item in content:
            # Check score threshold
            if item.score < min_score:
                continue

            # Check blocked keywords
            if blocked_keywords:
                text = f"{item.title} {item.summary}".lower()
                if any(keyword.lower() in text for keyword in blocked_keywords):
                    continue

            # Check segments
            if segments and item.meta_data:
                item_segments = item.meta_data.get("segments", [])
                if not any(seg in segments for seg in item_segments):
                    continue

            filtered.append(item)

        return filtered

    def score_content(
        self,
        content: List[ContentItem],
        preferences: Dict[str, Any],
        engagement: Dict[str, Any],
    ) -> List[tuple[ContentItem, float]]:
        """Score content based on personalization factors.

        Args:
            content: List of content items
            preferences: User preferences
            engagement: Engagement history

        Returns:
            List of (content, score) tuples
        """
        scored = []
        clicked_topics = engagement.get("clicked_topics", {})
        preferred_keywords = preferences.get("preferred_keywords", [])

        for item in content:
            score = item.score

            # Boost for clicked topics
            if item.meta_data:
                item_topics = item.meta_data.get("topics", [])
                for topic in item_topics:
                    if topic in clicked_topics:
                        score += clicked_topics[topic] * 5

            # Boost for preferred keywords
            if preferred_keywords:
                text = f"{item.title} {item.summary}".lower()
                for keyword in preferred_keywords:
                    if keyword.lower() in text:
                        score += 10

            # Recency boost
            if item.published_at:
                hours_old = (
                    datetime.utcnow() - item.published_at
                ).total_seconds() / 3600
                if hours_old < 24:
                    score += 20
                elif hours_old < 72:
                    score += 10

            scored.append((item, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def build_sections(
        self, scored_content: List[tuple[ContentItem, float]], max_articles: int
    ) -> List[Dict[str, Any]]:
        """Build newsletter sections from scored content.

        Args:
            scored_content: List of (content, score) tuples
            max_articles: Maximum number of articles

        Returns:
            List of sections
        """
        sections = []
        articles_by_category = {}

        # Group by category
        for item, score in scored_content[:max_articles]:
            category = "General"
            if item.meta_data and "category" in item.meta_data:
                category = item.meta_data["category"]

            if category not in articles_by_category:
                articles_by_category[category] = []

            articles_by_category[category].append(
                {
                    "title": item.title,
                    "url": item.url,
                    "author": item.author,
                    "summary": item.summary,
                    "published_at": item.published_at,
                    "score": score,
                    "metadata": item.meta_data,
                }
            )

        # Create sections
        priority_order = ["Trending", "Breaking", "Featured", "General"]

        for category in priority_order:
            if category in articles_by_category:
                sections.append(
                    {"title": category, "articles": articles_by_category[category]}
                )
                del articles_by_category[category]

        # Add remaining categories
        for category, articles in articles_by_category.items():
            sections.append({"title": category, "articles": articles})

        return sections

    def get_preferred_topics(self, engagement: Dict[str, Any]) -> List[str]:
        """Get subscriber's preferred topics.

        Args:
            engagement: Engagement history

        Returns:
            List of preferred topics
        """
        clicked_topics = engagement.get("clicked_topics", {})
        if not clicked_topics:
            return []

        # Sort by click count
        sorted_topics = sorted(clicked_topics.items(), key=lambda x: x[1], reverse=True)

        return [topic for topic, _ in sorted_topics[:5]]

    def get_optimal_send_time(self, subscriber_id: int) -> Optional[int]:
        """Get optimal send time for subscriber.

        Args:
            subscriber_id: Subscriber ID

        Returns:
            Optimal hour (0-23) or None
        """
        # Get open events with timestamps
        opens = (
            self.db.query(SubscriberEvent)
            .filter(
                SubscriberEvent.subscriber_id == subscriber_id,
                SubscriberEvent.event_type == EventType.OPEN,
            )
            .all()
        )

        if not opens:
            return None

        # Count opens by hour
        hour_counts = {}
        for event in opens:
            hour = event.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        # Find most common hour
        if hour_counts:
            return max(hour_counts, key=hour_counts.get)

        return None


class SegmentationEngine:
    """Engine for subscriber segmentation."""

    def __init__(self, db: Session):
        """Initialize segmentation engine.

        Args:
            db: Database session
        """
        self.db = db
        self.personalization = PersonalizationEngine(db)

    def segment_subscribers(self, newsletter_id: int) -> Dict[str, List[Subscriber]]:
        """Segment subscribers for newsletter.

        Args:
            newsletter_id: Newsletter ID

        Returns:
            Dictionary of segment name to subscriber list
        """
        segments = {
            "highly_engaged": [],
            "moderately_engaged": [],
            "low_engaged": [],
            "new": [],
            "at_risk": [],
            "inactive": [],
        }

        # Get all active subscribers
        from newsauto.models.newsletter import NewsletterSubscriber

        subscribers = (
            self.db.query(Subscriber)
            .join(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.newsletter_id == newsletter_id,
                NewsletterSubscriber.unsubscribed_at is None,
                Subscriber.status == "active",
            )
            .all()
        )

        for subscriber in subscribers:
            segment = self.determine_segment(subscriber, newsletter_id)
            segments[segment].append(subscriber)

        return segments

    def determine_segment(self, subscriber: Subscriber, newsletter_id: int) -> str:
        """Determine subscriber segment.

        Args:
            subscriber: Subscriber object
            newsletter_id: Newsletter ID

        Returns:
            Segment name
        """
        # Get engagement metrics
        engagement = self.personalization.get_engagement_history(
            subscriber.id, newsletter_id, days=30
        )

        score = engagement.get("score", 0)
        last_open = engagement.get("last_open")

        # New subscriber (less than 7 days)
        if (datetime.utcnow() - subscriber.subscribed_at).days < 7:
            return "new"

        # Check last open
        if last_open:
            days_since_open = (datetime.utcnow() - last_open).days

            if days_since_open > 60:
                return "inactive"
            elif days_since_open > 30:
                return "at_risk"

        # Score-based segmentation
        if score >= 10:
            return "highly_engaged"
        elif score >= 5:
            return "moderately_engaged"
        elif score >= 1:
            return "low_engaged"
        else:
            return "inactive"
