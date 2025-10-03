"""Command-line interface for Newsauto."""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from newsauto.automation.cron_manager import CronManager
from newsauto.automation.scheduler import NewsletterScheduler
from newsauto.automation.tasks import AutomationTasks, TaskRunner
from newsauto.core.config import get_settings
from newsauto.core.database import get_db, init_db
from newsauto.email.email_sender import SMTPConfig

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Newsauto CLI - Newsletter Automation System."""
    pass


@cli.command()
def init():
    """Initialize the database and create tables."""
    console.print("🚀 Initializing Newsauto database...", style="bold green")

    try:
        init_db()
        console.print("✅ Database initialized successfully!", style="green")

        # Create default templates
        from newsauto.generators.template_engine import TemplateEngine

        engine = TemplateEngine()
        engine.create_default_templates()
        console.print("✅ Default templates created!", style="green")

    except Exception as e:
        console.print(f"❌ Error initializing database: {e}", style="red")
        raise click.Abort()


@cli.command()
@click.option("--all-sources", is_flag=True, help="Fetch from all sources")
@click.option("--newsletter-id", type=int, help="Fetch for specific newsletter")
def fetch_content(all_sources, newsletter_id):
    """Fetch content from configured sources."""
    console.print("📡 Fetching content...", style="bold cyan")

    db = next(get_db())
    tasks = AutomationTasks(db)

    try:
        # Run async function
        import asyncio

        content = asyncio.run(tasks.fetch_content_all_sources())
        console.print(f"✅ Fetched {len(content)} content items", style="green")

        # Display summary table
        if content and isinstance(content, list):
            table = Table(title="Top Content")
            table.add_column("Title", style="cyan", max_width=50)
            table.add_column("Source", style="magenta")
            table.add_column("Score", style="green")

            # Limit to first 10 items
            display_items = content[:10] if len(content) > 10 else content
            for item in display_items:
                title = item.title[:50] if item.title else "No title"
                source = (
                    str(item.source_id) if hasattr(item, "source_id") else "Unknown"
                )
                score = str(round(item.score, 1)) if item.score else "0.0"
                table.add_row(title, source, score)

            console.print(table)

    except Exception as e:
        console.print(f"❌ Error fetching content: {e}", style="red")
        raise click.Abort()


@cli.command()
def process_scheduled():
    """Process scheduled newsletter sends."""
    console.print("⏰ Processing scheduled sends...", style="bold yellow")

    db = next(get_db())
    settings = get_settings()

    smtp_config = SMTPConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        from_email=settings.smtp_from,
        from_name="Newsauto",
    )

    from newsauto.email.delivery_manager import DeliveryManager

    delivery = DeliveryManager(db, smtp_config)

    try:
        import asyncio

        asyncio.run(delivery.process_scheduled_sends())
        console.print("✅ Scheduled sends processed", style="green")
    except Exception as e:
        console.print(f"❌ Error processing scheduled sends: {e}", style="red")
        raise click.Abort()


@cli.command()
def daily_maintenance():
    """Run daily maintenance tasks."""
    console.print("🔧 Running daily maintenance...", style="bold blue")

    db = next(get_db())
    tasks = AutomationTasks(db)

    try:
        # Run maintenance tasks
        import asyncio

        asyncio.run(tasks.cleanup_old_content())
        asyncio.run(tasks.process_subscriber_events())
        asyncio.run(tasks.validate_subscriber_emails())
        asyncio.run(tasks.optimize_send_times())
        asyncio.run(tasks.maintain_database())

        console.print("✅ Daily maintenance completed", style="green")
    except Exception as e:
        console.print(f"❌ Error in daily maintenance: {e}", style="red")
        raise click.Abort()


@cli.command()
@click.option("--newsletter-id", type=int, help="Generate for specific newsletter")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def generate_report(newsletter_id, format):
    """Generate analytics report."""
    console.print("📊 Generating analytics report...", style="bold magenta")

    db = next(get_db())
    tasks = AutomationTasks(db)

    try:
        import asyncio

        report = asyncio.run(tasks.generate_analytics_report(newsletter_id))

        if format == "json":
            import json

            console.print(json.dumps(report, indent=2))
        else:
            # Display as formatted text
            console.print("\n📈 Analytics Report", style="bold white")
            console.print(f"Generated: {report['generated_at']}")
            console.print(f"Period: {report['period']}\n")

            # Subscribers section
            console.print("👥 Subscribers", style="bold cyan")
            console.print(f"  Total: {report['subscribers']['total']}")
            console.print(f"  New: {report['subscribers']['new']}")
            console.print(f"  Growth: {report['subscribers']['growth_rate']:.1f}%\n")

            # Engagement section
            console.print("💌 Engagement", style="bold green")
            console.print(f"  Opens: {report['engagement']['total_opens']}")
            console.print(f"  Clicks: {report['engagement']['total_clicks']}")
            console.print(
                f"  Avg Open Rate: {report['engagement']['avg_open_rate']:.1f}%"
            )
            console.print(
                f"  Avg Click Rate: {report['engagement']['avg_click_rate']:.1f}%\n"
            )

    except Exception as e:
        console.print(f"❌ Error generating report: {e}", style="red")
        raise click.Abort()


@cli.command()
def setup_cron():
    """Set up cron jobs for automation."""
    console.print("⚙️ Setting up cron jobs...", style="bold yellow")

    cron = CronManager()

    try:
        if cron.setup_newsauto_jobs():
            console.print("✅ Cron jobs set up successfully!", style="green")

            # Display installed jobs
            jobs = cron.get_newsauto_jobs()
            if jobs:
                table = Table(title="Installed Cron Jobs")
                table.add_column("Schedule", style="cyan")
                table.add_column("Command", style="magenta", max_width=50)
                table.add_column("Description", style="green")

                for job in jobs:
                    table.add_row(job["schedule"], job["command"][:50], job["comment"])

                console.print(table)
        else:
            console.print("⚠️ Some cron jobs failed to install", style="yellow")

    except Exception as e:
        console.print(f"❌ Error setting up cron jobs: {e}", style="red")
        raise click.Abort()


@cli.command()
def remove_cron():
    """Remove all Newsauto cron jobs."""
    console.print("🗑️ Removing cron jobs...", style="bold red")

    if not click.confirm("Are you sure you want to remove all Newsauto cron jobs?"):
        console.print("Cancelled", style="yellow")
        return

    cron = CronManager()

    try:
        if cron.remove_newsauto_jobs():
            console.print("✅ Cron jobs removed successfully!", style="green")
        else:
            console.print("❌ Failed to remove cron jobs", style="red")

    except Exception as e:
        console.print(f"❌ Error removing cron jobs: {e}", style="red")
        raise click.Abort()


@cli.command()
def start_scheduler():
    """Start the newsletter scheduler service."""
    console.print("🚀 Starting newsletter scheduler...", style="bold green")

    db = next(get_db())
    settings = get_settings()

    smtp_config = SMTPConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        from_email=settings.smtp_from,
        from_name="Newsauto",
    )

    scheduler = NewsletterScheduler(db, smtp_config)
    runner = TaskRunner(db)

    async def run():
        try:
            # Start both scheduler and task runner
            await asyncio.gather(scheduler.start(), runner.start())
        except KeyboardInterrupt:
            console.print("\n⏹️ Stopping services...", style="yellow")
            await scheduler.stop()
            await runner.stop()
            console.print("✅ Services stopped", style="green")

    try:
        asyncio.run(run())
    except Exception as e:
        console.print(f"❌ Error running scheduler: {e}", style="red")
        raise click.Abort()


@cli.command()
@click.argument("email")
@click.option("--name", help="Subscriber name")
@click.option(
    "--newsletter-id", type=int, required=True, help="Newsletter to subscribe to"
)
def add_subscriber(email, name, newsletter_id):
    """Add a new subscriber."""
    console.print(f"➕ Adding subscriber {email}...", style="bold cyan")

    db = next(get_db())

    try:
        import secrets

        from newsauto.models.newsletter import Newsletter
        from newsauto.models.subscriber import NewsletterSubscriber, Subscriber

        # Check newsletter exists
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        if not newsletter:
            console.print(f"❌ Newsletter {newsletter_id} not found", style="red")
            raise click.Abort()

        # Create or get subscriber
        subscriber = db.query(Subscriber).filter(Subscriber.email == email).first()

        if not subscriber:
            subscriber = Subscriber(
                email=email,
                name=name,
                status="pending",
                verification_token=secrets.token_urlsafe(32),
            )
            db.add(subscriber)
            db.flush()

        # Subscribe to newsletter
        existing_sub = (
            db.query(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.newsletter_id == newsletter_id,
                NewsletterSubscriber.subscriber_id == subscriber.id,
            )
            .first()
        )

        if not existing_sub:
            newsletter_sub = NewsletterSubscriber(
                newsletter_id=newsletter_id, subscriber_id=subscriber.id
            )
            db.add(newsletter_sub)

        db.commit()
        console.print(
            f"✅ Subscriber {email} added to {newsletter.name}", style="green"
        )

    except Exception as e:
        console.print(f"❌ Error adding subscriber: {e}", style="red")
        db.rollback()
        raise click.Abort()


@cli.command()
@click.option("--name", required=True, help="Newsletter name")
@click.option("--description", help="Newsletter description")
@click.option(
    "--frequency", type=click.Choice(["daily", "weekly", "monthly"]), default="daily"
)
@click.option("--target-audience", help="Target audience description")
def create_newsletter(name, description, frequency, target_audience):
    """Create a new newsletter."""
    console.print(f"📰 Creating newsletter '{name}'...", style="bold green")

    db = next(get_db())

    try:

        from newsauto.models.newsletter import Newsletter

        newsletter = Newsletter(
            name=name,
            description=description or f"Newsletter about {name}",
            status="active",
            user_id=1,  # Default user_id
            settings={
                "frequency": frequency,
                "target_audience": target_audience or "General audience",
                "send_time": "09:00",  # Default 9 AM
                "max_articles": 10,
            },
        )

        db.add(newsletter)
        db.commit()

        console.print(
            f"✅ Newsletter '{name}' created with ID {newsletter.id}", style="green"
        )

    except Exception as e:
        console.print(f"❌ Error creating newsletter: {e}", style="red")
        db.rollback()
        raise click.Abort()


@cli.command()
def list_newsletters():
    """List all newsletters."""
    console.print("📋 Newsletters", style="bold white")

    db = next(get_db())

    try:
        from newsauto.models.newsletter import Newsletter

        newsletters = db.query(Newsletter).all()

        if not newsletters:
            console.print("No newsletters found", style="yellow")
            return

        table = Table(title="Newsletters")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Frequency", style="magenta")
        table.add_column("Subscribers", style="blue")
        table.add_column("Status", style="yellow")

        for nl in newsletters:
            table.add_row(
                str(nl.id),
                nl.name,
                nl.frequency or "N/A",
                str(nl.subscriber_count),
                nl.status,
            )

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error listing newsletters: {e}", style="red")
        raise click.Abort()


@cli.command()
@click.option("--newsletter-id", type=int, help="Newsletter ID")
@click.option("--newsletter-name", help="Newsletter name")
@click.option("--test-mode", is_flag=True, help="Generate test edition")
@click.option("--max-articles", default=10, help="Maximum articles to include")
def generate_test_newsletter(newsletter_id, newsletter_name, test_mode, max_articles):
    """Generate a test newsletter edition."""
    try:
        db = next(get_db())

        from newsauto.models.newsletter import Newsletter

        # Find newsletter
        if newsletter_id:
            newsletter = (
                db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
            )
        elif newsletter_name:
            newsletter = (
                db.query(Newsletter).filter(Newsletter.name == newsletter_name).first()
            )
        else:
            # Use first active newsletter
            newsletter = (
                db.query(Newsletter).filter(Newsletter.status == "active").first()
            )

        if not newsletter:
            console.print("❌ Newsletter not found", style="red")
            raise click.Abort()

        console.print(f"🔄 Generating test newsletter for: {newsletter.name}")

        # Generate edition
        from newsauto.generators.newsletter_generator import NewsletterGenerator

        generator = NewsletterGenerator(db)

        edition = generator.generate_edition(
            newsletter, test_mode=True, max_articles=max_articles
        )

        console.print(f"✅ Generated edition ID: {edition.id}", style="green")
        console.print(f"   Subject: {edition.subject}")
        console.print(f"   Articles: {edition.content.get('total_articles', 0)}")

    except Exception as e:
        console.print(f"❌ Error generating newsletter: {e}", style="red")
        raise click.Abort()


@cli.command()
@click.option(
    "--newsletter-id", type=int, required=True, help="Newsletter to add sources to"
)
@click.option(
    "--niche",
    help="Niche to get sources for (e.g., 'AI & Machine Learning', 'DevOps')",
)
@click.option("--confirm/--no-confirm", default=True, help="Confirm before adding")
def add_default_sources(newsletter_id, niche, confirm):
    """Add high-quality default content sources to a newsletter."""
    console.print(
        f"🔧 Adding default sources to newsletter {newsletter_id}...", style="bold cyan"
    )

    db = next(get_db())

    try:
        from newsauto.models.content import ContentSource, ContentSourceType
        from newsauto.models.newsletter import Newsletter
        from newsauto.scrapers.default_sources import get_sources_for_niche

        # Check newsletter exists
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        if not newsletter:
            console.print(
                f"❌ Newsletter with ID {newsletter_id} not found", style="red"
            )
            return

        # Get niche from newsletter if not specified
        if not niche:
            niche = newsletter.niche or "General Tech"

        # Get recommended sources
        sources = get_sources_for_niche(niche)

        if not sources:
            console.print(
                f"⚠️ No default sources found for niche: {niche}", style="yellow"
            )
            return

        console.print(f"\n📋 Found {len(sources)} recommended sources for '{niche}':\n")

        # Display sources
        table = Table(title="Recommended Sources")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("URL/Config", style="green", max_width=50)

        for source in sources:
            url_or_config = source.get("url") or str(source.get("config", {}))
            table.add_row(source["name"], source["type"], url_or_config[:50])

        console.print(table)

        # Confirm addition
        if confirm:
            if not click.confirm(
                f"\nAdd these {len(sources)} sources to {newsletter.name}?"
            ):
                console.print("Cancelled", style="yellow")
                return

        # Add sources
        added_count = 0
        skipped_count = 0

        for source_data in sources:
            # Check if source already exists
            existing = (
                db.query(ContentSource)
                .filter(
                    ContentSource.newsletter_id == newsletter_id,
                    ContentSource.name == source_data["name"],
                )
                .first()
            )

            if existing:
                console.print(
                    f"⏩ Skipping {source_data['name']} (already exists)",
                    style="yellow",
                )
                skipped_count += 1
                continue

            # Create new source
            source_type = ContentSourceType[source_data["type"].upper()]
            source = ContentSource(
                newsletter_id=newsletter_id,
                name=source_data["name"],
                type=source_type,
                url=source_data.get("url", ""),
                config=source_data.get("config", {}),
                active=True,
                fetch_frequency_minutes=60,
            )

            db.add(source)
            added_count += 1
            console.print(f"✅ Added {source_data['name']}", style="green")

        db.commit()

        console.print(
            f"\n✅ Complete! Added {added_count} sources, skipped {skipped_count} existing",
            style="bold green",
        )

    except Exception as e:
        console.print(f"❌ Error adding sources: {e}", style="red")
        db.rollback()
        raise click.Abort()


@cli.command()
@click.option("--email", required=True, help="Email address to send to")
@click.option("--edition-id", type=int, help="Edition ID to send")
@click.option("--subject", default="Test Newsletter", help="Email subject")
def send_test_email(email, edition_id, subject):
    """Send a test email."""
    import asyncio

    async def _send():
        try:
            db = next(get_db())

            if edition_id:
                # Send specific edition
                from newsauto.models.edition import Edition

                edition = db.query(Edition).filter(Edition.id == edition_id).first()

                if not edition:
                    console.print("❌ Edition not found", style="red")
                    return

                # Render edition
                from newsauto.generators.newsletter_generator import NewsletterGenerator

                generator = NewsletterGenerator(db)
                html_content, text_content = generator.render_edition(edition)
                subject = edition.subject
            else:
                # Send test content
                html_content = """
                <html>
                    <body>
                        <h1>Test Newsletter</h1>
                        <p>This is a test email from the Newsletter system.</p>
                        <p>If you received this, email sending is working!</p>
                    </body>
                </html>
                """
                text_content = "Test Newsletter\n\nThis is a test email."

            # Send email
            from newsauto.core.config import get_settings
            from newsauto.email.email_sender import EmailSender, SMTPConfig

            settings = get_settings()
            smtp_config = SMTPConfig(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=settings.smtp_tls,
                from_email=(
                    settings.smtp_from.split("<")[1].strip(">")
                    if "<" in settings.smtp_from
                    else settings.smtp_from
                ),
                from_name=(
                    settings.smtp_from.split("<")[0].strip()
                    if "<" in settings.smtp_from
                    else "Newsletter"
                ),
            )

            sender = EmailSender(smtp_config)
            success = await sender.send_email(
                to_email=email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

            if success:
                console.print(f"✅ Test email sent to {email}", style="green")
            else:
                console.print("❌ Failed to send email", style="red")

        except Exception as e:
            console.print(f"❌ Error: {e}", style="red")

    asyncio.run(_send())


@cli.command()
@click.option("--newsletter-id", type=int, help="Newsletter ID")
@click.option("--output", default="preview.html", help="Output file path")
def preview_newsletter(newsletter_id, output):
    """Generate HTML preview of newsletter."""
    try:
        db = next(get_db())

        from newsauto.models.newsletter import Newsletter

        # Find newsletter
        if newsletter_id:
            newsletter = (
                db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
            )
        else:
            newsletter = (
                db.query(Newsletter).filter(Newsletter.status == "active").first()
            )

        if not newsletter:
            console.print("❌ Newsletter not found", style="red")
            raise click.Abort()

        console.print(f"🔄 Generating preview for: {newsletter.name}")

        # Generate preview
        from newsauto.generators.newsletter_generator import NewsletterGenerator

        generator = NewsletterGenerator(db)

        preview = generator.preview_edition(newsletter_id=newsletter.id)

        # Save preview
        from pathlib import Path

        output_path = Path(output)
        output_path.write_text(preview["html"])

        console.print(f"✅ Preview saved to: {output_path}", style="green")
        console.print(f"   Subject: {preview['subject']}")

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise click.Abort()


if __name__ == "__main__":
    cli()
