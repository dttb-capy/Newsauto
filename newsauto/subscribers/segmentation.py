"""
Subscriber segmentation system for targeted newsletter delivery.
Segments subscribers based on engagement, preferences, and behavior.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SegmentType(Enum):
    """Types of subscriber segments."""

    ENGAGEMENT = "engagement"  # Based on open/click rates
    PREFERENCE = "preference"  # Based on content preferences
    DEMOGRAPHIC = "demographic"  # Based on company/role
    BEHAVIORAL = "behavioral"  # Based on actions taken
    LIFECYCLE = "lifecycle"  # Based on subscription age
    VALUE = "value"  # Based on revenue potential


class EngagementLevel(Enum):
    """Subscriber engagement levels."""

    HIGHLY_ENGAGED = "highly_engaged"  # >60% open rate
    ENGAGED = "engaged"  # 30-60% open rate
    MODERATE = "moderate"  # 15-30% open rate
    LOW = "low"  # 5-15% open rate
    INACTIVE = "inactive"  # <5% open rate
    NEW = "new"  # <30 days old, insufficient data


class SubscriberTier(Enum):
    """Subscriber value tiers."""

    ENTERPRISE = "enterprise"  # Enterprise customers
    PREMIUM = "premium"  # Paid individual subscribers
    TEAM = "team"  # Team subscriptions
    FREE = "free"  # Free tier
    TRIAL = "trial"  # Trial period


@dataclass
class SegmentCriteria:
    """Criteria for defining a subscriber segment."""

    name: str
    segment_type: SegmentType
    conditions: Dict[str, Any]
    priority: int = 1
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class SubscriberProfile:
    """Complete profile of a subscriber for segmentation."""

    subscriber_id: int
    email: str
    company: Optional[str] = None
    role: Optional[str] = None
    tier: SubscriberTier = SubscriberTier.FREE

    # Engagement metrics
    total_sent: int = 0
    total_opens: int = 0
    total_clicks: int = 0
    last_open_date: Optional[datetime] = None
    last_click_date: Optional[datetime] = None
    open_rate: float = 0.0
    click_rate: float = 0.0

    # Preferences
    preferred_topics: List[str] = field(default_factory=list)
    preferred_send_time: Optional[str] = None
    frequency_preference: Optional[str] = None
    content_type_preference: Optional[str] = None

    # Behavioral data
    signup_date: datetime = None
    subscription_age_days: int = 0
    referred_subscribers: int = 0
    support_tickets: int = 0
    feedback_submitted: int = 0

    # Segments
    segments: List[str] = field(default_factory=list)
    engagement_level: Optional[EngagementLevel] = None

    # Technical attributes
    email_client: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None


class SubscriberSegmentation:
    """Manages subscriber segmentation for targeted delivery."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize segmentation system."""
        self.db_session = db_session
        self.predefined_segments = self._initialize_segments()

    def _initialize_segments(self) -> Dict[str, SegmentCriteria]:
        """Initialize predefined segment criteria."""
        return {
            # Engagement-based segments
            "power_users": SegmentCriteria(
                name="Power Users",
                segment_type=SegmentType.ENGAGEMENT,
                conditions={
                    "open_rate_min": 0.6,
                    "click_rate_min": 0.2,
                    "last_open_days": 7,
                },
                priority=10,
                description="Highly engaged subscribers who consistently interact",
                tags=["high_value", "engaged"],
            ),
            "at_risk": SegmentCriteria(
                name="At Risk",
                segment_type=SegmentType.ENGAGEMENT,
                conditions={
                    "open_rate_max": 0.3,
                    "last_open_days_min": 14,
                    "last_open_days_max": 30,
                },
                priority=8,
                description="Previously engaged subscribers showing declining activity",
                tags=["retention", "re-engagement"],
            ),
            "dormant": SegmentCriteria(
                name="Dormant",
                segment_type=SegmentType.ENGAGEMENT,
                conditions={"last_open_days_min": 30, "open_rate_max": 0.05},
                priority=3,
                description="Inactive subscribers for re-engagement campaigns",
                tags=["inactive", "win-back"],
            ),
            # Value-based segments
            "enterprise_accounts": SegmentCriteria(
                name="Enterprise Accounts",
                segment_type=SegmentType.VALUE,
                conditions={"tier": SubscriberTier.ENTERPRISE, "company_size_min": 500},
                priority=10,
                description="High-value enterprise customers",
                tags=["enterprise", "high_value"],
            ),
            "premium_engaged": SegmentCriteria(
                name="Premium Engaged",
                segment_type=SegmentType.VALUE,
                conditions={"tier": SubscriberTier.PREMIUM, "open_rate_min": 0.4},
                priority=9,
                description="Engaged paying subscribers",
                tags=["premium", "engaged"],
            ),
            # Demographic segments
            "faang_engineers": SegmentCriteria(
                name="FAANG Engineers",
                segment_type=SegmentType.DEMOGRAPHIC,
                conditions={
                    "companies": [
                        "Google",
                        "Apple",
                        "Meta",
                        "Amazon",
                        "Netflix",
                        "Microsoft",
                    ],
                    "roles": ["engineer", "developer", "architect", "sre"],
                },
                priority=9,
                description="Engineers at top tech companies",
                tags=["tech", "high_value"],
            ),
            "startup_founders": SegmentCriteria(
                name="Startup Founders",
                segment_type=SegmentType.DEMOGRAPHIC,
                conditions={
                    "roles": ["founder", "ceo", "cto", "co-founder"],
                    "company_size_max": 50,
                },
                priority=8,
                description="Startup founders and early-stage leaders",
                tags=["startup", "decision_maker"],
            ),
            # Behavioral segments
            "referral_champions": SegmentCriteria(
                name="Referral Champions",
                segment_type=SegmentType.BEHAVIORAL,
                conditions={"referred_subscribers_min": 3},
                priority=9,
                description="Subscribers who actively refer others",
                tags=["advocate", "referral"],
            ),
            "feedback_providers": SegmentCriteria(
                name="Feedback Providers",
                segment_type=SegmentType.BEHAVIORAL,
                conditions={"feedback_submitted_min": 2},
                priority=7,
                description="Active feedback providers",
                tags=["engaged", "feedback"],
            ),
            # Lifecycle segments
            "new_subscribers": SegmentCriteria(
                name="New Subscribers",
                segment_type=SegmentType.LIFECYCLE,
                conditions={"subscription_age_days_max": 30},
                priority=8,
                description="Recently joined subscribers in onboarding phase",
                tags=["new", "onboarding"],
            ),
            "veterans": SegmentCriteria(
                name="Veterans",
                segment_type=SegmentType.LIFECYCLE,
                conditions={"subscription_age_days_min": 365, "open_rate_min": 0.3},
                priority=7,
                description="Long-term engaged subscribers",
                tags=["loyal", "veteran"],
            ),
            # Preference segments
            "morning_readers": SegmentCriteria(
                name="Morning Readers",
                segment_type=SegmentType.PREFERENCE,
                conditions={"preferred_send_times": ["6AM", "7AM", "8AM", "9AM"]},
                priority=5,
                description="Prefer morning delivery",
                tags=["timing", "morning"],
            ),
            "mobile_first": SegmentCriteria(
                name="Mobile First",
                segment_type=SegmentType.PREFERENCE,
                conditions={"device_types": ["mobile", "tablet"]},
                priority=6,
                description="Primarily read on mobile devices",
                tags=["mobile", "responsive"],
            ),
        }

    def calculate_engagement_level(self, profile: SubscriberProfile) -> EngagementLevel:
        """Calculate engagement level for a subscriber."""
        if profile.subscription_age_days < 30:
            return EngagementLevel.NEW

        if profile.total_sent == 0:
            return EngagementLevel.NEW

        if profile.open_rate >= 0.6:
            return EngagementLevel.HIGHLY_ENGAGED
        elif profile.open_rate >= 0.3:
            return EngagementLevel.ENGAGED
        elif profile.open_rate >= 0.15:
            return EngagementLevel.MODERATE
        elif profile.open_rate >= 0.05:
            return EngagementLevel.LOW
        else:
            return EngagementLevel.INACTIVE

    def segment_subscriber(
        self,
        profile: SubscriberProfile,
        custom_segments: Optional[List[SegmentCriteria]] = None,
    ) -> List[str]:
        """
        Determine which segments a subscriber belongs to.

        Args:
            profile: Subscriber profile with metrics
            custom_segments: Additional custom segment criteria

        Returns:
            List of segment names the subscriber belongs to
        """
        segments = []

        # Calculate engagement level
        profile.engagement_level = self.calculate_engagement_level(profile)

        # Check predefined segments
        for segment_name, criteria in self.predefined_segments.items():
            if self._matches_criteria(profile, criteria):
                segments.append(segment_name)

        # Check custom segments
        if custom_segments:
            for criteria in custom_segments:
                if self._matches_criteria(profile, criteria):
                    segments.append(criteria.name)

        # Add engagement level as a segment
        segments.append(f"engagement_{profile.engagement_level.value}")

        # Add tier as a segment
        segments.append(f"tier_{profile.tier.value}")

        return segments

    def _matches_criteria(
        self, profile: SubscriberProfile, criteria: SegmentCriteria
    ) -> bool:
        """Check if a subscriber matches segment criteria."""
        conditions = criteria.conditions

        # Engagement conditions
        if "open_rate_min" in conditions:
            if profile.open_rate < conditions["open_rate_min"]:
                return False

        if "open_rate_max" in conditions:
            if profile.open_rate > conditions["open_rate_max"]:
                return False

        if "click_rate_min" in conditions:
            if profile.click_rate < conditions["click_rate_min"]:
                return False

        if "last_open_days" in conditions:
            if profile.last_open_date:
                days_since = (datetime.now() - profile.last_open_date).days
                if days_since > conditions["last_open_days"]:
                    return False

        if "last_open_days_min" in conditions:
            if profile.last_open_date:
                days_since = (datetime.now() - profile.last_open_date).days
                if days_since < conditions["last_open_days_min"]:
                    return False

        if "last_open_days_max" in conditions:
            if profile.last_open_date:
                days_since = (datetime.now() - profile.last_open_date).days
                if days_since > conditions["last_open_days_max"]:
                    return False

        # Value conditions
        if "tier" in conditions:
            if profile.tier != conditions["tier"]:
                return False

        # Demographic conditions
        if "companies" in conditions:
            if not profile.company or profile.company not in conditions["companies"]:
                return False

        if "roles" in conditions:
            if not profile.role:
                return False
            role_lower = profile.role.lower()
            if not any(role in role_lower for role in conditions["roles"]):
                return False

        if "company_size_min" in conditions:
            # This would require additional company data
            pass

        if "company_size_max" in conditions:
            # This would require additional company data
            pass

        # Behavioral conditions
        if "referred_subscribers_min" in conditions:
            if profile.referred_subscribers < conditions["referred_subscribers_min"]:
                return False

        if "feedback_submitted_min" in conditions:
            if profile.feedback_submitted < conditions["feedback_submitted_min"]:
                return False

        # Lifecycle conditions
        if "subscription_age_days_min" in conditions:
            if profile.subscription_age_days < conditions["subscription_age_days_min"]:
                return False

        if "subscription_age_days_max" in conditions:
            if profile.subscription_age_days > conditions["subscription_age_days_max"]:
                return False

        # Preference conditions
        if "preferred_send_times" in conditions:
            if not profile.preferred_send_time:
                return False
            if profile.preferred_send_time not in conditions["preferred_send_times"]:
                return False

        if "device_types" in conditions:
            if not profile.device_type:
                return False
            if profile.device_type not in conditions["device_types"]:
                return False

        return True

    async def get_segment_subscribers(
        self, segment_name: str, limit: Optional[int] = None
    ) -> List[int]:
        """
        Get subscriber IDs belonging to a specific segment.

        Args:
            segment_name: Name of the segment
            limit: Maximum number of subscribers to return

        Returns:
            List of subscriber IDs
        """
        # This would query the database for subscribers matching segment criteria
        # Implementation depends on your model structure
        pass

    def get_segment_size(self, segment_name: str) -> int:
        """Get the number of subscribers in a segment."""
        # This would count subscribers in the database
        pass

    def calculate_segment_metrics(self, segment_name: str) -> Dict[str, Any]:
        """Calculate aggregate metrics for a segment."""
        # This would aggregate metrics for all subscribers in segment
        return {
            "size": 0,
            "avg_open_rate": 0.0,
            "avg_click_rate": 0.0,
            "revenue_potential": 0.0,
            "churn_risk": 0.0,
        }

    def recommend_segments(self, profile: SubscriberProfile) -> List[Dict[str, Any]]:
        """
        Recommend potential segments for targeting.

        Args:
            profile: Subscriber profile

        Returns:
            List of recommended segments with reasons
        """
        recommendations = []

        # Check for upsell opportunities
        if profile.tier == SubscriberTier.FREE and profile.open_rate > 0.4:
            recommendations.append(
                {
                    "segment": "upsell_candidate",
                    "reason": "High engagement on free tier",
                    "action": "Send premium features showcase",
                }
            )

        # Check for re-engagement needs
        if profile.engagement_level in [EngagementLevel.LOW, EngagementLevel.MODERATE]:
            if profile.last_open_date:
                days_inactive = (datetime.now() - profile.last_open_date).days
                if 7 < days_inactive < 30:
                    recommendations.append(
                        {
                            "segment": "re_engagement",
                            "reason": f"No opens in {days_inactive} days",
                            "action": "Send re-engagement campaign",
                        }
                    )

        # Check for referral potential
        if (
            profile.engagement_level == EngagementLevel.HIGHLY_ENGAGED
            and profile.referred_subscribers == 0
        ):
            recommendations.append(
                {
                    "segment": "referral_potential",
                    "reason": "Highly engaged but hasn't referred",
                    "action": "Send referral incentive",
                }
            )

        return recommendations

    def export_segment_data(self, segment_name: str, format: str = "csv") -> str:
        """Export segment data for external use."""
        # Implementation for exporting segment data
        pass
