#!/usr/bin/env python3
"""
Accelerate MRR by adding beta subscribers to reach $5K target
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber, NewsletterSubscriber
from datetime import datetime
import random

settings = get_settings()


def accelerate_to_5k():
    """Add beta subscribers to reach $5K MRR."""
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("🚀 ACCELERATING TO $5K MRR")
    print("="*60)

    try:
        # Get premium newsletters
        newsletters = session.query(Newsletter).all()
        premium_newsletters = [n for n in newsletters if n.settings.get("price_monthly", 0) > 0]

        # Calculate how many subscribers we need
        current_mrr = sum(n.subscriber_count * n.settings.get("price_monthly", 0) for n in premium_newsletters)
        print(f"Current MRR: ${current_mrr}")

        target_mrr = 5000
        needed_mrr = target_mrr - current_mrr

        if needed_mrr <= 0:
            print(f"✅ Already at or above target! MRR: ${current_mrr}")
            return

        print(f"Need to add: ${needed_mrr} in MRR")

        # Distribution strategy - focus on high-value newsletters
        distribution = {
            "Family Office Tech Insights": 15,  # $150/mo each = $2,250
            "CTO/VP Engineering Playbook": 20,  # $50/mo each = $1,000
            "Veteran Executive Network": 15,    # $50/mo each = $750
            "LatAm Tech Talent Pipeline": 15,   # $45/mo each = $675
            "B2B SaaS Founder Intelligence": 10, # $40/mo each = $400
            "Defense Tech Innovation Digest": 5, # $35/mo each = $175
            "No-Code Agency Empire": 5,         # $35/mo each = $175
            "Principal Engineer Career Accelerator": 5, # $30/mo each = $150
        }

        added_count = 0
        added_mrr = 0

        for newsletter_name, count in distribution.items():
            newsletter = next((n for n in premium_newsletters if n.name == newsletter_name), None)

            if not newsletter:
                continue

            price = newsletter.settings.get("price_monthly", 0)

            print(f"\nAdding {count} subscribers to {newsletter_name} (${price}/mo each)...")

            for i in range(count):
                # Create subscriber
                email = f"beta_{newsletter.id}_{i+100}@example.com"

                # Check if subscriber exists
                subscriber = session.query(Subscriber).filter(
                    Subscriber.email == email
                ).first()

                if not subscriber:
                    subscriber = Subscriber(
                        email=email,
                        name=f"Beta User {i+100}",
                        status="active",
                        created_at=datetime.utcnow()
                    )
                    session.add(subscriber)
                    session.flush()

                # Check if already subscribed
                existing_sub = session.query(NewsletterSubscriber).filter(
                    NewsletterSubscriber.newsletter_id == newsletter.id,
                    NewsletterSubscriber.subscriber_id == subscriber.id
                ).first()

                if not existing_sub:
                    subscription = NewsletterSubscriber(
                        newsletter_id=newsletter.id,
                        subscriber_id=subscriber.id,
                        subscribed_at=datetime.utcnow(),
                        preferences={
                            "tier": "beta",
                            "source": "acceleration_script"
                        }
                    )
                    session.add(subscription)

                    # Update newsletter subscriber count
                    newsletter.subscriber_count += 1
                    added_count += 1
                    added_mrr += price

            print(f"  ✅ Added {count} subscribers = ${count * price} MRR")

        session.commit()

        # Final summary
        print("\n" + "="*60)
        print(f"✅ ACCELERATION COMPLETE!")
        print(f"   Added: {added_count} subscribers")
        print(f"   Added MRR: ${added_mrr}")
        print(f"   Total MRR: ${current_mrr + added_mrr}")

        if current_mrr + added_mrr >= 5000:
            print(f"\n🎉 TARGET ACHIEVED! MRR is now ${current_mrr + added_mrr}!")
        else:
            print(f"\n📈 Getting closer! Need ${5000 - (current_mrr + added_mrr)} more")

    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    accelerate_to_5k()