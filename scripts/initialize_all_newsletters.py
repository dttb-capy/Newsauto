#!/usr/bin/env python3
"""
Initialize all 10 premium newsletters in the database.
Sets up complete configuration for the zero-touch automation army.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.base import BaseModel
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.subscriber import Subscriber, NewsletterSubscriber
from newsauto.models.content import ContentSource
from newsauto.models.user import User
from newsauto.config.niches import NEWSLETTER_NICHES
import bcrypt
from datetime import datetime

settings = get_settings()

# Newsletter configurations with all details
NEWSLETTER_CONFIGS = [
    {
        "key": "cto_engineering_playbook",
        "name": "CTO/VP Engineering Playbook",
        "description": "Strategic insights for CTOs and VPs scaling engineering teams at Series A-D startups",
        "niche": "engineering_leadership",
        "price": 50,
        "send_time": "07:00",
        "frequency": "weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "b2b_saas_founders",
        "name": "B2B SaaS Founder Intelligence",
        "description": "Strategic insights for B2B SaaS founders scaling from $1M to $100M ARR",
        "niche": "saas_business",
        "price": 40,
        "send_time": "08:00",
        "frequency": "weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "principal_engineer_career",
        "name": "Principal Engineer Career Accelerator",
        "description": "Strategic career guidance for senior engineers targeting Principal/Distinguished roles",
        "niche": "career_development",
        "price": 30,
        "send_time": "18:00",
        "frequency": "bi-weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "defense_tech_innovation",
        "name": "Defense Tech Innovation Digest",
        "description": "DoD procurement opportunities and defense tech innovation for contractors and startups",
        "niche": "defense_technology",
        "price": 35,
        "send_time": "07:00",
        "frequency": "weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "veteran_executive_network",
        "name": "Veteran Executive Network",
        "description": "Strategic insights for veteran CEOs, board members, and tech leaders",
        "niche": "veteran_business",
        "price": 50,
        "send_time": "06:00",
        "frequency": "bi-weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "latam_tech_talent",
        "name": "LatAm Tech Talent Pipeline",
        "description": "Strategic guide for US companies hiring elite Latin American developers",
        "niche": "talent_acquisition",
        "price": 45,
        "send_time": "10:00",
        "frequency": "bi-weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "faith_enterprise_tech",
        "name": "Faith-Based Enterprise Tech",
        "description": "Digital transformation for faith-based organizations and religious enterprises",
        "niche": "faith_technology",
        "price": 25,
        "send_time": "09:00",
        "frequency": "bi-weekly",
        "template": "technical_newsletter.html"
    },
    {
        "key": "family_office_tech",
        "name": "Family Office Tech Insights",
        "description": "Technology investment insights for family offices and HNW individuals",
        "niche": "investment_tech",
        "price": 150,
        "send_time": "07:00",
        "frequency": "weekly",
        "template": "executive_newsletter.html"
    },
    {
        "key": "no_code_agency_empire",
        "name": "No-Code Agency Empire",
        "description": "Scale from freelancer to $1M+ agency with no-code tools",
        "niche": "agency_business",
        "price": 35,
        "send_time": "09:00",
        "frequency": "weekly",
        "template": "technical_newsletter.html"
    },
    {
        "key": "tech_succession_planning",
        "name": "Tech Succession Planning",
        "description": "Preparing family businesses for digital transformation and succession",
        "niche": "succession_planning",
        "price": 40,
        "send_time": "08:00",
        "frequency": "monthly",
        "template": "technical_newsletter.html"
    }
]


def initialize_database():
    """Initialize database and create tables."""
    engine = create_engine(settings.database_url)
    BaseModel.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def create_admin_user(session):
    """Create admin user if not exists."""
    admin = session.query(User).filter(User.email == "admin@newsauto.io").first()

    if not admin:
        # Try with username first
        admin = session.query(User).filter(User.username == "admin").first()

    if not admin:
        hashed_password = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
        admin = User(
            email="admin@newsauto.io",
            username="admin",
            password_hash=hashed_password.decode(),
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        session.commit()
        print("✅ Created admin user: admin@newsauto.io")
    else:
        print("ℹ️  Admin user already exists")

    return admin


def create_test_subscriber(session):
    """Create test subscriber erick.durantt@gmail.com."""
    subscriber = session.query(Subscriber).filter(
        Subscriber.email == "erick.durantt@gmail.com"
    ).first()

    if not subscriber:
        subscriber = Subscriber(
            email="erick.durantt@gmail.com",
            first_name="Erick",
            last_name="Durantt",
            status="active",
            preferences={
                "send_time": "08:00",
                "timezone": "America/New_York",
                "content_types": ["executive", "technical", "strategic"],
                "beta_tester": True
            },
            tags=["beta", "vip", "founder"],
            created_at=datetime.utcnow()
        )
        session.add(subscriber)
        session.commit()
        print("✅ Created test subscriber: erick.durantt@gmail.com")

    return subscriber


def create_newsletters(session, admin_user):
    """Create all 10 premium newsletters."""
    created_count = 0

    for config in NEWSLETTER_CONFIGS:
        # Check if newsletter exists
        newsletter = session.query(Newsletter).filter(
            Newsletter.name == config["name"]
        ).first()

        if not newsletter:
            # Get full niche configuration
            niche_config = NEWSLETTER_NICHES.get(config["key"])

            newsletter = Newsletter(
                name=config["name"],
                niche=config["niche"],
                description=config["description"],
                template_id=1,  # Default template
                user_id=admin_user.id,
                status=NewsletterStatus.ACTIVE,
                settings={
                    "frequency": config["frequency"],
                    "send_time": config["send_time"],
                    "timezone": "America/New_York",
                    "max_articles": 10,
                    "price_monthly": config["price"],
                    "price_annual": config["price"] * 10,  # 2 months free
                    "template": config["template"],
                    "target_open_rate": niche_config.target_open_rate if niche_config else 0.40,
                    "target_click_rate": niche_config.target_click_rate if niche_config else 0.05,
                    "enable_tracking": True,
                    "enable_analytics": True,
                    "enable_personalization": True,
                    "content_ratio": niche_config.content_ratio if niche_config else {
                        "original": 0.65,
                        "curated": 0.25,
                        "syndicated": 0.10
                    },
                    "summarization_prompt": niche_config.summarization_prompt if niche_config else "",
                    "tone_style": niche_config.tone_style if niche_config else "executive"
                },
                subscriber_count=0,
                created_at=datetime.utcnow()
            )
            session.add(newsletter)
            created_count += 1
            print(f"✅ Created newsletter: {config['name']} (${config['price']}/month)")
        else:
            print(f"ℹ️  Newsletter already exists: {config['name']}")

    session.commit()
    return created_count


def create_content_sources(session):
    """Create content sources for each newsletter."""
    created_count = 0

    for config_key, niche_config in NEWSLETTER_NICHES.items():
        # Find the newsletter
        newsletter_name = next(
            (c["name"] for c in NEWSLETTER_CONFIGS if c["key"] == config_key),
            None
        )

        if not newsletter_name:
            continue

        newsletter = session.query(Newsletter).filter(
            Newsletter.name == newsletter_name
        ).first()

        if not newsletter:
            continue

        # Add content sources
        for source in niche_config.content_sources[:5]:  # Limit to 5 per newsletter for now
            existing = session.query(ContentSource).filter(
                ContentSource.url == source.url,
                ContentSource.newsletter_id == newsletter.id
            ).first()

            if not existing:
                content_source = ContentSource(
                    newsletter_id=newsletter.id,
                    name=source.name,
                    url=source.url,
                    type="rss",  # Hardcode as RSS for now
                    active=True,  # Changed from is_active to active
                    config={
                        "priority": source.priority,
                        "filters": source.filters
                    },
                    created_at=datetime.utcnow()
                )
                session.add(content_source)
                created_count += 1

        if created_count > 0:
            print(f"✅ Added {created_count} content sources for {newsletter_name}")

    session.commit()
    return created_count


def subscribe_test_user(session, subscriber):
    """Subscribe test user to all newsletters."""
    newsletters = session.query(Newsletter).filter(
        Newsletter.status == NewsletterStatus.ACTIVE
    ).all()

    subscribed_count = 0

    for newsletter in newsletters:
        # Check if already subscribed
        existing = session.query(NewsletterSubscriber).filter(
            NewsletterSubscriber.newsletter_id == newsletter.id,
            NewsletterSubscriber.subscriber_id == subscriber.id
        ).first()

        if not existing:
            subscription = NewsletterSubscriber(
                newsletter_id=newsletter.id,
                subscriber_id=subscriber.id,
                subscribed_at=datetime.utcnow(),
                preferences={
                    "beta_tester": True,
                    "send_all": True,
                    "tier": "beta"
                }
            )
            session.add(subscription)

            # Update subscriber count
            newsletter.subscriber_count += 1
            subscribed_count += 1
            print(f"✅ Subscribed to: {newsletter.name}")

    session.commit()
    return subscribed_count


def calculate_revenue_potential():
    """Calculate and display revenue potential."""
    print("\n" + "="*70)
    print("💰 REVENUE POTENTIAL CALCULATION")
    print("="*70)

    total_monthly = 0

    print("\nWith 146 subscribers per newsletter (Portuguese Model):")
    print("-"*50)

    for config in NEWSLETTER_CONFIGS:
        monthly_revenue = config["price"] * 146
        total_monthly += monthly_revenue
        print(f"{config['name'][:40]:<40} ${config['price']:>3}/mo = ${monthly_revenue:>7,}/mo")

    print("-"*50)
    print(f"{'TOTAL MONTHLY REVENUE':<40} = ${total_monthly:>7,}/mo")
    print(f"{'ANNUAL REVENUE':<40} = ${total_monthly * 12:>7,}/yr")
    print(f"{'OPERATING COSTS':<40} = $     10/mo")
    print(f"{'NET MONTHLY PROFIT':<40} = ${total_monthly - 10:>7,}/mo")
    print(f"{'PROFIT MARGIN':<40} = {((total_monthly - 10) / total_monthly * 100):>6.2f}%")

    print("\n" + "="*70)
    print("📈 GROWTH TRAJECTORY")
    print("="*70)

    milestones = [
        (10, "Week 1: Beta Launch"),
        (50, "Month 1: Early Access"),
        (100, "Month 2: Growth Phase"),
        (146, "Month 3: Portuguese Model"),
        (500, "Year 1: Scale Target")
    ]

    for subs, label in milestones:
        monthly = int(total_monthly * subs / 146)
        print(f"{label:<30} {subs:>3} subs = ${monthly:>7,}/mo")


def main():
    """Main initialization function."""
    print("🚀 NEWSAUTO PREMIUM NEWSLETTER INITIALIZATION")
    print("="*70)

    # Initialize database
    print("\n📊 Initializing database...")
    session = initialize_database()

    try:
        # Create admin user
        admin = create_admin_user(session)

        # Create test subscriber
        subscriber = create_test_subscriber(session)

        # Create newsletters
        print("\n📰 Creating premium newsletters...")
        newsletter_count = create_newsletters(session, admin)

        # Create content sources
        print("\n🌐 Setting up content sources...")
        source_count = create_content_sources(session)

        # Subscribe test user
        print("\n📧 Subscribing test user to all newsletters...")
        subscription_count = subscribe_test_user(session, subscriber)

        # Calculate revenue
        calculate_revenue_potential()

        # Summary
        print("\n" + "="*70)
        print("✅ INITIALIZATION COMPLETE")
        print("="*70)
        print(f"• Created {newsletter_count} new newsletters")
        print(f"• Added {source_count} content sources")
        print(f"• Subscribed to {subscription_count} newsletters")
        print(f"• Test email: erick.durantt@gmail.com")
        print(f"• Admin login: admin@newsauto.io / admin123")
        print("\n🎯 Next Steps:")
        print("1. Run: python scripts/content_army.py")
        print("2. Run: python scripts/revenue_battalion.py")
        print("3. Run: python scripts/battle_dashboard.py")
        print("4. Check email for all 10 newsletters!")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()