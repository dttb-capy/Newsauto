"""
Executive email delivery system for premium newsletters.
Handles personalization, scheduling, and optimal delivery for C-suite audiences.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
import pytz
from jinja2 import Environment, FileSystemLoader, select_autoescape

from newsauto.core.config import get_settings

settings = get_settings()
from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.email.delivery_manager import DeliveryManager
from newsauto.email.tracking import EmailTracker
from newsauto.subscribers.segmentation import (
    SubscriberSegmentation,
    SubscriberProfile,
    SubscriberTier,
    EngagementLevel
)
from newsauto.delivery.ab_testing import ABTestingManager
from newsauto.config.niches import niche_configs
import asyncio

logger = logging.getLogger(__name__)


class ExecutiveEmailDelivery:
    """Handles email delivery for executive audiences."""

    def __init__(self):
        """Initialize the executive email delivery system."""
        # Create SMTP config from settings
        smtp_config = SMTPConfig(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
            from_email=settings.smtp_from,
            from_name="Newsauto Premium"
        )
        self.sender = EmailSender(smtp_config)
        self.delivery_manager = DeliveryManager()
        self.tracker = EmailTracker()
        self.segmentation = SubscriberSegmentation()
        self.ab_testing = ABTestingManager()

        # Setup Jinja2 for templates
        self.template_env = Environment(
            loader=FileSystemLoader("newsauto/templates"),
            autoescape=select_autoescape(["html", "xml"])
        )

    def get_optimal_send_time(
        self,
        subscriber: SubscriberProfile,
        niche_key: str
    ) -> datetime:
        """
        Determine optimal send time for an executive subscriber.

        Based on research:
        - Tuesday-Thursday perform best
        - 9-10 AM local time for executives
        - Avoid Mondays (planning) and Fridays (wrap-up)
        """
        # Get subscriber timezone (default to Eastern)
        tz_str = subscriber.timezone or "America/New_York"
        try:
            tz = pytz.timezone(tz_str)
        except:
            tz = pytz.timezone("America/New_York")

        # Get current time in subscriber's timezone
        now = datetime.now(tz)

        # Find next optimal day (Tuesday-Thursday)
        days_ahead = 0
        while True:
            check_date = now + timedelta(days=days_ahead)
            # Tuesday = 1, Wednesday = 2, Thursday = 3
            if check_date.weekday() in [1, 2, 3]:
                break
            days_ahead += 1
            if days_ahead > 7:  # Safety check
                break

        # Set to 9 AM local time
        send_date = now + timedelta(days=days_ahead)
        send_time = tz.localize(datetime.combine(
            send_date.date(),
            time(9, 0)  # 9 AM
        ))

        # Override with niche-specific timing if available
        if niche_key in niche_configs:
            niche = niche_configs[niche_key]
            # Parse optimal send time from niche config
            # e.g., "Tuesday 9AM EST"
            # This is simplified - in production would have more robust parsing

        return send_time

    def personalize_content(
        self,
        template_name: str,
        subscriber: SubscriberProfile,
        content: Dict[str, Any],
        niche_key: str
    ) -> str:
        """
        Personalize newsletter content for executive subscriber.

        Args:
            template_name: Name of the template to use
            subscriber: Subscriber profile
            content: Newsletter content data
            niche_key: Niche identifier

        Returns:
            Personalized HTML content
        """
        # Load template
        if template_name == "executive":
            template = self.template_env.get_template("executive_newsletter.html")
        else:
            template = self.template_env.get_template(f"{template_name}_newsletter.html")

        # Get niche configuration
        niche = niche_configs.get(niche_key, None)

        # Prepare personalization data
        personalization = {
            # Subscriber data
            "subscriber_name": self._get_formal_name(subscriber),
            "subscriber_company": subscriber.company,
            "subscriber_role": subscriber.role,
            "subscriber_tier": subscriber.tier.value if subscriber.tier else "free",

            # Newsletter data
            "newsletter": {
                "name": niche.name if niche else "Newsletter",
                "value_proposition": niche.value_proposition if niche else "",
            },

            # Content sections
            "executive_takeaways": content.get("takeaways", []),
            "strategic_insights": content.get("insights", []),
            "market_intelligence": content.get("market_intel", []),
            "recommended_actions": content.get("actions", []),

            # Metadata
            "current_date": datetime.now(),
            "edition": content.get("edition", "Executive Edition"),

            # URLs
            "dashboard_url": f"{settings.app_url}/dashboard",
            "preferences_url": f"{settings.app_url}/preferences",
            "unsubscribe_url": self.tracker.generate_unsubscribe_link(
                subscriber.email, niche_key
            ),
            "refer_url": f"{settings.app_url}/refer",

            # Tracking
            "tracking_pixel": self.tracker.add_tracking_pixel(
                f"open_{subscriber.subscriber_id}_{datetime.now().strftime('%Y%m%d')}"
            )
        }

        # Add premium features for paid tiers
        if subscriber.tier.value in ["premium", "enterprise"]:
            personalization.update({
                "premium_content": content.get("premium", []),
                "exclusive_insights": content.get("exclusive", []),
                "subscriber_value": "Premium Member",
            })

        # Render template
        html_content = template.render(**personalization)

        # Track links for analytics
        html_content = self.tracker.track_links(
            html_content,
            campaign_id=f"{niche_key}_{datetime.now().strftime('%Y%m%d')}"
        )

        return html_content

    def _get_formal_name(self, subscriber: SubscriberProfile) -> str:
        """Get formal name for executive addressing."""
        if subscriber.company and subscriber.role:
            # For C-suite, use title
            if any(title in subscriber.role.lower() for title in ["ceo", "cto", "cfo", "vp"]):
                return subscriber.role

        # Default to email prefix
        email_name = subscriber.email.split("@")[0]
        # Capitalize properly
        return " ".join(word.capitalize() for word in email_name.replace(".", " ").split())

    async def send_executive_newsletter(
        self,
        subscriber: SubscriberProfile,
        niche_key: str,
        content: Dict[str, Any],
        test_mode: bool = False
    ) -> bool:
        """
        Send newsletter to an executive subscriber.

        Args:
            subscriber: Subscriber profile
            niche_key: Niche identifier
            content: Newsletter content
            test_mode: Whether this is a test send

        Returns:
            True if sent successfully
        """
        try:
            # Get niche configuration
            niche = niche_configs.get(niche_key)
            if not niche:
                logger.error(f"Niche {niche_key} not found")
                return False

            # Generate subject line using A/B testing
            subject_patterns = {
                "executive_authority": [
                    f"Board Brief: {content.get('main_topic', 'Strategic Update')}"
                ],
                "strategic_urgency": [
                    f"Q{(datetime.now().month-1)//3+1} Priority: {content.get('main_topic', 'Action Items')}"
                ],
            }

            subject = self.ab_testing.select_best_subject(
                newsletter_id=1,  # Would be actual newsletter ID
                default_subject=f"{niche.name}: {content.get('main_topic', 'Executive Update')}"
            )

            # Personalize content
            html_content = self.personalize_content(
                "executive",
                subscriber,
                content,
                niche_key
            )

            # Prepare email
            email_data = {
                "to": subscriber.email,
                "subject": subject,
                "html": html_content,
                "headers": {
                    "List-Unsubscribe": f"<{self.tracker.generate_unsubscribe_link(subscriber.email, niche_key)}>",
                    "X-Newsletter": niche.name,
                    "X-Subscriber-Tier": subscriber.tier.value,
                }
            }

            # Send email
            if test_mode:
                logger.info(f"TEST MODE: Would send to {subscriber.email}")
                return True
            else:
                result = await self.sender.send_email(**email_data)

                if result:
                    logger.info(f"Sent {niche.name} to {subscriber.email}")
                    # Track delivery
                    await self._track_delivery(subscriber, niche_key, subject)

                return result

        except Exception as e:
            logger.error(f"Error sending to {subscriber.email}: {e}")
            return False

    async def _track_delivery(
        self,
        subscriber: SubscriberProfile,
        niche_key: str,
        subject: str
    ):
        """Track email delivery metrics."""
        # This would integrate with your analytics system
        delivery_data = {
            "subscriber_id": subscriber.subscriber_id,
            "niche": niche_key,
            "subject": subject,
            "sent_at": datetime.now(),
            "tier": subscriber.tier.value,
            "segment": subscriber.engagement_level.value if subscriber.engagement_level else "unknown"
        }

        # Log for now - would save to database
        logger.info(f"Delivery tracked: {delivery_data}")

    async def send_batch_to_segment(
        self,
        segment_name: str,
        niche_key: str,
        content: Dict[str, Any],
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send newsletter to a specific segment.

        Args:
            segment_name: Name of the segment
            niche_key: Niche identifier
            content: Newsletter content
            limit: Maximum number to send

        Returns:
            Delivery statistics
        """
        stats = {
            "segment": segment_name,
            "niche": niche_key,
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "start_time": datetime.now()
        }

        # Get subscribers in segment
        # This would query your database
        subscribers = []  # Would be actual subscriber list

        if limit:
            subscribers = subscribers[:limit]

        stats["attempted"] = len(subscribers)

        # Send to each subscriber
        for subscriber in subscribers:
            result = await self.send_executive_newsletter(
                subscriber, niche_key, content
            )

            if result:
                stats["successful"] += 1
            else:
                stats["failed"] += 1

            # Rate limiting for premium delivery
            # Executives expect quality over speed
            await asyncio.sleep(0.5)  # Half second between sends

        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).seconds

        logger.info(f"Batch send complete: {stats}")
        return stats


class ExecutiveDeliveryScheduler:
    """Schedules optimal delivery times for executive newsletters."""

    def __init__(self):
        self.delivery = ExecutiveEmailDelivery()

    def schedule_daily_sends(self) -> List[Dict[str, Any]]:
        """
        Schedule daily newsletter sends at optimal times.

        Returns:
            List of scheduled send jobs
        """
        scheduled = []

        for niche_key, niche in niche_configs.items():
            # Parse frequency from niche config
            if niche.frequency == "daily":
                send_time = self._parse_optimal_time(niche.optimal_send_time)
                scheduled.append({
                    "niche": niche_key,
                    "time": send_time,
                    "frequency": "daily",
                    "segments": ["power_users", "enterprise_accounts"]
                })
            elif niche.frequency == "weekly":
                # Weekly sends on best day (usually Tuesday)
                scheduled.append({
                    "niche": niche_key,
                    "time": "Tuesday 9AM EST",
                    "frequency": "weekly",
                    "segments": ["all_active"]
                })

        return scheduled

    def _parse_optimal_time(self, time_str: str) -> str:
        """Parse optimal send time from configuration."""
        # Simple implementation - would be more robust in production
        return time_str or "9AM EST"


# Test function
async def test_executive_delivery():
    """Test executive email delivery system."""
    import asyncio

    delivery = ExecutiveEmailDelivery()

    # Create test subscriber
    test_subscriber = SubscriberProfile(
        subscriber_id=1,
        email="test@example.com",
        company="Test Corp",
        role="CTO",
        tier=SubscriberTier.ENTERPRISE,
        open_rate=0.65,
        engagement_level=EngagementLevel.HIGHLY_ENGAGED
    )

    # Test content
    test_content = {
        "main_topic": "AI Infrastructure Scaling",
        "edition": "Tuesday Edition",
        "takeaways": [
            "Cloud costs reduced 40% with new architecture",
            "Team velocity increased 2.5x with AI tools",
            "Security posture improved with zero-trust model"
        ],
        "insights": [
            {
                "title": "Scaling AI Infrastructure at 10x Lower Cost",
                "summary": "How leading companies are optimizing GPU usage...",
                "impact": "High Impact",
                "timeframe": "Q1 2025",
                "url": "https://example.com/insight1"
            }
        ],
        "actions": [
            {
                "text": "Review Q1 infrastructure budget allocation",
                "deadline": "End of Week"
            },
            {
                "text": "Schedule architecture review with engineering leads",
                "deadline": "Next Tuesday"
            }
        ]
    }

    # Test send
    result = await delivery.send_executive_newsletter(
        test_subscriber,
        "cto_engineering_playbook",
        test_content,
        test_mode=True
    )

    print(f"Test delivery result: {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_executive_delivery())