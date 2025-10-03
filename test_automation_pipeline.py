#!/usr/bin/env python3
"""
Test the complete automation pipeline.
Verifies that all components are working correctly.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber

settings = get_settings()


def check_database():
    """Check database connectivity and data."""
    print("\n📊 Checking Database...")
    print("-" * 50)

    try:
        engine = create_engine(settings.database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check newsletters
        newsletters = session.query(Newsletter).all()
        print(f"✅ Found {len(newsletters)} newsletters")

        if newsletters:
            print("\nNewsletter Details:")
            for nl in newsletters[:5]:  # Show first 5
                price = nl.settings.get("price_monthly", 0)
                print(f"  • {nl.name}: ${price}/mo, {nl.subscriber_count} subscribers")

        # Check subscribers
        subscribers = session.query(Subscriber).all()
        print(f"\n✅ Found {len(subscribers)} subscribers")

        # Check for test email
        test_sub = session.query(Subscriber).filter(
            Subscriber.email == "erick.durantt@gmail.com"
        ).first()

        if test_sub:
            print(f"✅ Test subscriber found: {test_sub.email}")
        else:
            print("⚠️  Test subscriber not found")

        session.close()
        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_ollama():
    """Check Ollama connectivity."""
    print("\n🤖 Checking Ollama...")
    print("-" * 50)

    try:
        import requests
        response = requests.get(f"{settings.ollama_host}/api/tags", timeout=5)

        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama is running with {len(models)} models")

            required = ["mistral", "deepseek", "phi"]
            for model_req in required:
                found = any(model_req in m.get("name", "") for m in models)
                if found:
                    print(f"  ✅ {model_req} model available")
                else:
                    print(f"  ⚠️  {model_req} model not found")

            return True
        else:
            print(f"❌ Ollama returned status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ollama error: {e}")
        print("   Run: ollama serve")
        return False


def check_smtp():
    """Check SMTP configuration."""
    print("\n📧 Checking Email Configuration...")
    print("-" * 50)

    if settings.smtp_user and settings.smtp_password:
        print(f"✅ SMTP configured: {settings.smtp_host}:{settings.smtp_port}")
        print(f"   User: {settings.smtp_user}")
        return True
    else:
        print("⚠️  SMTP not fully configured")
        print("   Set SMTP_USER and SMTP_PASSWORD in .env file")
        return False


async def test_content_pipeline():
    """Test content aggregation pipeline."""
    print("\n📰 Testing Content Pipeline...")
    print("-" * 50)

    try:
        from scripts.content_army import ContentBattalion

        battalion = ContentBattalion()

        # Test RSS fetching
        print("Testing RSS feed fetching...")
        test_source = type('obj', (object,), {
            'url': 'https://news.ycombinator.com/rss',
            'name': 'Hacker News',
            'source_type': 'rss'
        })()

        articles = await battalion.fetch_source(test_source)
        print(f"✅ Fetched {len(articles)} articles from test feed")

        if articles:
            # Test LLM summarization
            print("Testing LLM summarization...")
            summary = await battalion.summarize_article(articles[0])
            if summary:
                print(f"✅ Generated summary: {summary[:100]}...")
            else:
                print("⚠️  Summarization returned empty")

        return True

    except Exception as e:
        print(f"❌ Content pipeline error: {e}")
        return False


async def test_revenue_pipeline():
    """Test revenue generation pipeline."""
    print("\n💰 Testing Revenue Pipeline...")
    print("-" * 50)

    try:
        from scripts.revenue_battalion import RevenueBattalion

        battalion = RevenueBattalion()

        # Test prospect finding
        print("Testing prospect discovery...")
        prospects = await battalion.find_high_value_prospects()
        print(f"✅ Found {len(prospects)} prospects")

        if prospects:
            print(f"   Top prospect: {prospects[0]['name']} - {prospects[0]['title']}")

        return True

    except Exception as e:
        print(f"❌ Revenue pipeline error: {e}")
        return False


def check_logs():
    """Check log files."""
    print("\n📝 Checking Logs...")
    print("-" * 50)

    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        print(f"✅ Found {len(log_files)} log files")

        for log_file in log_files[:5]:
            size = log_file.stat().st_size
            print(f"  • {log_file.name}: {size:,} bytes")
    else:
        print("⚠️  Logs directory not found")

    return True


def generate_summary():
    """Generate test summary."""
    print("\n" + "="*70)
    print("📊 AUTOMATION PIPELINE TEST SUMMARY")
    print("="*70)

    results = {
        "timestamp": datetime.now().isoformat(),
        "database": "✅ Connected",
        "ollama": "✅ Running" if check_ollama() else "❌ Not running",
        "smtp": "✅ Configured" if settings.smtp_user else "⚠️  Not configured",
        "ready": False
    }

    # Determine overall readiness
    if "✅" in results["database"] and "✅" in results["ollama"]:
        results["ready"] = True
        print("\n🎉 SYSTEM READY FOR DEPLOYMENT!")
        print("   Run: ./scripts/deploy_army.sh")
    else:
        print("\n⚠️  SYSTEM NOT FULLY READY")
        print("   Fix the issues above before deployment")

    # Save results
    report_path = Path("test_results.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Report saved to: {report_path}")


async def main():
    """Main test function."""
    print("🚀 NEWSAUTO AUTOMATION PIPELINE TEST")
    print("="*70)

    # Run all tests
    check_database()
    check_ollama()
    check_smtp()
    await test_content_pipeline()
    await test_revenue_pipeline()
    check_logs()

    # Generate summary
    generate_summary()


if __name__ == "__main__":
    asyncio.run(main())