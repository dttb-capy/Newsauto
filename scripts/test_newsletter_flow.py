#!/usr/bin/env python3
"""Manual test script for newsletter generation and email sending."""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from newsauto.core.database import SessionLocal, engine
from newsauto.models.base import Base
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.subscriber import Subscriber, SubscriberStatus
from newsauto.models.content import ContentItem
from newsauto.generators.newsletter_generator import NewsletterGenerator
from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.scrapers.aggregator import ContentAggregator
from newsauto.llm.ollama_client import OllamaClient

console = Console()


async def setup_test_data(db):
    """Create test newsletter and subscribers."""
    console.print("\n[bold cyan]Setting up test data...[/bold cyan]")

    # Check for existing test newsletter
    newsletter = db.query(Newsletter).filter(
        Newsletter.name == "Test Newsletter"
    ).first()

    if not newsletter:
        newsletter = Newsletter(
            name="Test Newsletter",
            description="A test newsletter for manual testing",
            niche="Technology",
            user_id=1,  # Assuming default user
            status=NewsletterStatus.ACTIVE,
            settings={
                "frequency": "daily",
                "send_time": datetime.now().time().strftime("%H:%M"),
                "max_articles": 10,
                "target_audience": "Developers and tech enthusiasts"
            }
        )
        db.add(newsletter)
        db.commit()
        console.print("✅ Created test newsletter")
    else:
        console.print("✅ Found existing test newsletter")

    # Check for test subscribers
    test_emails = [
        "test1@mailhog.local",
        "test2@mailhog.local",
        "test3@mailhog.local"
    ]

    for email in test_emails:
        subscriber = db.query(Subscriber).filter(
            Subscriber.email == email
        ).first()

        if not subscriber:
            subscriber = Subscriber(
                email=email,
                name=f"Test User {email.split('@')[0]}",
                status=SubscriberStatus.ACTIVE,
                verified_at=datetime.utcnow()
            )
            db.add(subscriber)
            db.commit()  # Commit subscriber first

            # Create newsletter-subscriber relationship
            from newsauto.models.subscriber import NewsletterSubscriber
            ns = NewsletterSubscriber(
                newsletter_id=newsletter.id,
                subscriber_id=subscriber.id
            )
            db.add(ns)

    db.commit()
    console.print(f"✅ Set up {len(test_emails)} test subscribers")

    return newsletter


async def fetch_test_content(db, newsletter_id):
    """Fetch or create test content."""
    console.print("\n[bold cyan]Preparing content...[/bold cyan]")

    # Check for recent content
    recent = datetime.utcnow() - timedelta(hours=24)
    content = db.query(ContentItem).filter(
        ContentItem.fetched_at >= recent
    ).limit(10).all()

    if len(content) < 5:
        console.print("Creating sample content...")

        # Create test content
        sample_articles = [
            {
                "title": "Breaking: AI Model Achieves New Breakthrough in Language Understanding",
                "content": "Researchers have announced a significant breakthrough in AI language models...",
                "author": "Tech Reporter",
                "category": "AI & Machine Learning"
            },
            {
                "title": "Cloud Computing Trends 2025: What Developers Need to Know",
                "content": "The cloud computing landscape continues to evolve rapidly with new services...",
                "author": "Cloud Expert",
                "category": "Cloud & Infrastructure"
            },
            {
                "title": "Security Alert: New Vulnerability Discovered in Popular Framework",
                "content": "A critical security vulnerability has been identified in a widely-used framework...",
                "author": "Security Team",
                "category": "Security"
            },
            {
                "title": "Open Source Project Reaches Major Milestone",
                "content": "The popular open-source project has reached an important milestone with...",
                "author": "Community Lead",
                "category": "Open Source"
            },
            {
                "title": "Developer Survey Reveals Surprising Trends in Programming Languages",
                "content": "The latest developer survey shows interesting shifts in language preferences...",
                "author": "Data Analyst",
                "category": "Programming"
            }
        ]

        for i, article in enumerate(sample_articles):
            item = ContentItem(
                title=article["title"],
                content=article["content"] * 20,  # Make content longer
                summary=article["content"][:150] + "...",
                url=f"https://example.com/article-{i+1}",
                author=article["author"],
                published_at=datetime.utcnow() - timedelta(hours=i*2),
                fetched_at=datetime.utcnow(),
                score=90 - i*5,
                meta_data={
                    "category": article["category"],
                    "newsletter_id": newsletter_id
                }
            )
            db.add(item)

        db.commit()
        content = db.query(ContentItem).filter(
            ContentItem.fetched_at >= recent
        ).all()

    console.print(f"✅ Found {len(content)} content items")
    return content


async def test_newsletter_generation(db, newsletter):
    """Test newsletter generation."""
    console.print("\n[bold cyan]Testing Newsletter Generation[/bold cyan]")

    # Initialize generator
    try:
        llm_client = OllamaClient()
        await llm_client.check_connection()
        console.print("✅ Connected to Ollama")
    except Exception as e:
        console.print(f"[yellow]⚠️  Ollama not available: {e}[/yellow]")
        console.print("Using mock LLM client for testing")
        llm_client = None

    generator = NewsletterGenerator(db, llm_client=llm_client)

    # Generate edition
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating newsletter edition...", total=None)

        try:
            edition = generator.generate_edition(
                newsletter,
                test_mode=True,
                max_articles=5,
                min_score=50.0
            )
            progress.update(task, completed=True)

            console.print(f"✅ Generated edition ID: {edition.id}")
            console.print(f"   Subject: [green]{edition.subject}[/green]")
            console.print(f"   Articles: {edition.content.get('total_articles', 0)}")

            # Display sections
            sections_table = Table(title="Newsletter Sections")
            sections_table.add_column("Section", style="cyan")
            sections_table.add_column("Articles", style="magenta")

            for section in edition.content.get('sections', []):
                sections_table.add_row(
                    section['title'],
                    str(len(section.get('articles', [])))
                )

            console.print(sections_table)

            return edition

        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]❌ Generation failed: {e}[/red]")
            return None


async def test_email_rendering(db, generator, edition):
    """Test email template rendering."""
    console.print("\n[bold cyan]Testing Email Rendering[/bold cyan]")

    try:
        # Get a test subscriber
        subscriber = db.query(Subscriber).first()

        # Render email
        html_content, text_content = generator.render_edition(edition, subscriber)

        console.print("✅ Email rendered successfully")
        console.print(f"   HTML size: {len(html_content)} bytes")
        console.print(f"   Text size: {len(text_content)} bytes")

        # Save preview files
        preview_dir = Path("data/previews")
        preview_dir.mkdir(parents=True, exist_ok=True)

        html_file = preview_dir / f"preview_{edition.id}.html"
        text_file = preview_dir / f"preview_{edition.id}.txt"

        with open(html_file, 'w') as f:
            f.write(html_content)

        with open(text_file, 'w') as f:
            f.write(text_content)

        console.print(f"   Preview saved to: {html_file}")

        return html_content, text_content

    except Exception as e:
        console.print(f"[red]❌ Rendering failed: {e}[/red]")
        return None, None


async def test_email_sending(edition, html_content, text_content):
    """Test sending emails via MailHog."""
    console.print("\n[bold cyan]Testing Email Sending[/bold cyan]")

    # Configure for MailHog (development SMTP)
    smtp_config = SMTPConfig(
        host="localhost",
        port=1025,
        use_tls=False,
        from_email="newsletter@test.local",
        from_name="Test Newsletter System"
    )

    sender = EmailSender(smtp_config)

    try:
        # Send test email
        success = await sender.send_email(
            to_email="test@mailhog.local",
            subject=edition.subject,
            html_content=html_content,
            text_content=text_content,
            headers={
                'X-Newsletter-ID': str(edition.newsletter_id),
                'X-Edition-ID': str(edition.id)
            }
        )

        if success:
            console.print("✅ Email sent successfully to MailHog")
            console.print("   View at: http://localhost:8025")
        else:
            console.print("[yellow]⚠️  Email sending failed[/yellow]")

        return success

    except Exception as e:
        console.print(f"[red]❌ SMTP Error: {e}[/red]")
        console.print("\n[yellow]Make sure MailHog is running:[/yellow]")
        console.print("  docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog")
        return False


async def run_interactive_test():
    """Run interactive test flow."""
    console.print(Panel.fit(
        "[bold green]Newsletter System Test Suite[/bold green]\n"
        "This script will test newsletter generation and email sending",
        border_style="green"
    ))

    db = SessionLocal()

    try:
        # Step 1: Setup
        newsletter = await setup_test_data(db)

        # Step 2: Content
        content = await fetch_test_content(db, newsletter.id)

        # Step 3: Generation
        console.print("\n" + "="*50)
        if console.input("[bold]Generate newsletter? (y/n): [/bold]").lower() == 'y':
            generator = NewsletterGenerator(db)
            edition = await test_newsletter_generation(db, newsletter)

            if edition:
                # Step 4: Rendering
                console.print("\n" + "="*50)
                if console.input("[bold]Render email templates? (y/n): [/bold]").lower() == 'y':
                    html_content, text_content = await test_email_rendering(
                        db, generator, edition
                    )

                    if html_content:
                        # Step 5: Sending
                        console.print("\n" + "="*50)
                        if console.input("[bold]Send test email? (y/n): [/bold]").lower() == 'y':
                            await test_email_sending(edition, html_content, text_content)

        # Summary
        console.print("\n" + "="*50)
        console.print(Panel.fit(
            "[bold cyan]Test Complete![/bold cyan]\n\n"
            "Results:\n"
            f"✓ Newsletter: {newsletter.name}\n"
            f"✓ Subscribers: {len(newsletter.subscribers)}\n"
            f"✓ Content Items: {len(content)}\n"
            f"✓ Latest Edition: #{getattr(edition, 'id', 'N/A')}",
            border_style="cyan"
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Test cancelled by user[/yellow]")

    except Exception as e:
        console.print(f"\n[red]Test failed with error: {e}[/red]")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


async def quick_test():
    """Run quick automated test."""
    console.print("[bold]Running quick automated test...[/bold]\n")

    db = SessionLocal()

    try:
        # Setup
        newsletter = await setup_test_data(db)
        content = await fetch_test_content(db, newsletter.id)

        # Generate
        generator = NewsletterGenerator(db)
        edition = await test_newsletter_generation(db, newsletter)

        if edition:
            # Render
            html, text = await test_email_rendering(db, generator, edition)

            # Try to send (will fail gracefully if MailHog not running)
            if html:
                await test_email_sending(edition, html, text)

        console.print("\n[bold green]Quick test completed![/bold green]")

    finally:
        db.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test newsletter generation and sending")
    parser.add_argument('--quick', action='store_true', help='Run quick automated test')
    parser.add_argument('--interactive', action='store_true', help='Run interactive test')

    args = parser.parse_args()

    if args.quick:
        asyncio.run(quick_test())
    else:
        asyncio.run(run_interactive_test())


if __name__ == "__main__":
    main()