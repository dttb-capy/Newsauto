#!/usr/bin/env python3
"""
Battle Dashboard: Real-time monitoring and command center for the automation army.
Tracks all metrics, performance, and revenue in real-time.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import json
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.subscriber import Subscriber, NewsletterSubscriber
from newsauto.models.edition import Edition, EditionStats
from newsauto.config.niches import NEWSLETTER_NICHES, calculate_potential_revenue

console = Console()
settings = get_settings()


class BattleDashboard:
    """Real-time monitoring dashboard for all operations."""

    def __init__(self):
        """Initialize the dashboard."""
        self.engine = create_engine(settings.database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.metrics = {}
        self.running = True

    async def start_monitoring(self):
        """Start real-time monitoring."""
        console.print("[bold cyan]🎯 NEWSAUTO BATTLE DASHBOARD[/bold cyan]")
        console.print("[yellow]Real-time monitoring of all automation operations[/yellow]\n")

        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", size=20),
            Layout(name="footer", size=3)
        )

        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        with Live(layout, refresh_per_second=1, console=console) as live:
            while self.running:
                try:
                    # Update metrics
                    await self.update_metrics()

                    # Update display
                    layout["header"].update(self.create_header())
                    layout["left"].update(self.create_revenue_panel())
                    layout["right"].update(self.create_operations_panel())
                    layout["footer"].update(self.create_footer())

                    await asyncio.sleep(5)  # Update every 5 seconds

                except KeyboardInterrupt:
                    self.running = False
                    console.print("\n[red]Dashboard stopped by user[/red]")
                    break
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    await asyncio.sleep(5)

    async def update_metrics(self):
        """Update all metrics from database and logs."""
        session = self.Session()

        try:
            # Newsletter metrics
            newsletters = session.query(Newsletter).filter(
                Newsletter.status == NewsletterStatus.ACTIVE
            ).all()

            self.metrics["total_newsletters"] = len(newsletters)
            self.metrics["newsletters"] = []

            total_subscribers = 0
            total_mrr = 0

            for newsletter in newsletters:
                subscribers = newsletter.subscriber_count
                price = newsletter.settings.get("price_monthly", 0)
                mrr = subscribers * price

                total_subscribers += subscribers
                total_mrr += mrr

                self.metrics["newsletters"].append({
                    "name": newsletter.name,
                    "subscribers": subscribers,
                    "price": price,
                    "mrr": mrr,
                    "niche": newsletter.niche
                })

            self.metrics["total_subscribers"] = total_subscribers
            self.metrics["total_mrr"] = total_mrr

            # Subscriber metrics
            all_subscribers = session.query(Subscriber).count()
            active_subscribers = session.query(Subscriber).filter(
                Subscriber.status == "active"
            ).count()

            self.metrics["all_subscribers"] = all_subscribers
            self.metrics["active_subscribers"] = active_subscribers

            # Edition metrics
            total_editions = session.query(Edition).count()
            sent_editions = session.query(Edition).filter(
                Edition.status == "sent"
            ).count()

            self.metrics["total_editions"] = total_editions
            self.metrics["sent_editions"] = sent_editions

            # Load operation reports if they exist
            self.load_operation_reports()

            # Calculate projections
            self.calculate_projections()

        finally:
            session.close()

    def load_operation_reports(self):
        """Load reports from operation battalions."""
        # Load content army report
        content_report_path = Path("logs/content_army_report.json")
        if content_report_path.exists():
            with open(content_report_path) as f:
                content_report = json.load(f)
                self.metrics["content_ops"] = content_report.get("stats", {})
        else:
            self.metrics["content_ops"] = {
                "feeds_processed": 0,
                "articles_fetched": 0,
                "articles_summarized": 0,
                "newsletters_generated": 0,
                "emails_sent": 0
            }

        # Load revenue battalion report
        revenue_report_path = Path("logs/revenue_battalion_report.json")
        if revenue_report_path.exists():
            with open(revenue_report_path) as f:
                revenue_report = json.load(f)
                self.metrics["revenue_ops"] = revenue_report.get("stats", {})
        else:
            self.metrics["revenue_ops"] = {
                "prospects_found": 0,
                "outreach_sent": 0,
                "trials_started": 0,
                "conversions": 0,
                "mrr_added": 0
            }

    def calculate_projections(self):
        """Calculate revenue projections."""
        current_mrr = self.metrics["total_mrr"]

        # Growth projections (assuming 20% month-over-month growth)
        self.metrics["projections"] = {
            "next_month": int(current_mrr * 1.2),
            "3_months": int(current_mrr * (1.2 ** 3)),
            "6_months": int(current_mrr * (1.2 ** 6)),
            "1_year": int(current_mrr * (1.2 ** 12))
        }

        # Path to targets
        self.metrics["path_to_5k"] = max(0, 5000 - current_mrr)
        self.metrics["path_to_10k"] = max(0, 10000 - current_mrr)
        self.metrics["path_to_50k"] = max(0, 50000 - current_mrr)

        # Subscribers needed (assuming $45 average)
        avg_price = 45
        self.metrics["subs_for_5k"] = int(self.metrics["path_to_5k"] / avg_price)
        self.metrics["subs_for_10k"] = int(self.metrics["path_to_10k"] / avg_price)
        self.metrics["subs_for_50k"] = int(self.metrics["path_to_50k"] / avg_price)

    def create_header(self):
        """Create header panel."""
        return Panel(
            f"[bold cyan]NEWSAUTO COMMAND CENTER[/bold cyan] | "
            f"[green]MRR: ${self.metrics.get('total_mrr', 0):,}[/green] | "
            f"[yellow]Subscribers: {self.metrics.get('total_subscribers', 0)}[/yellow] | "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="bold white on blue"
        )

    def create_revenue_panel(self):
        """Create revenue metrics panel."""
        table = Table(title="💰 Revenue Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        # Current metrics
        table.add_row("Current MRR", f"${self.metrics.get('total_mrr', 0):,}")
        table.add_row("Total Subscribers", str(self.metrics.get('total_subscribers', 0)))
        table.add_row("Active Newsletters", str(self.metrics.get('total_newsletters', 0)))

        # Projections
        if "projections" in self.metrics:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Projections[/bold]", "")
            table.add_row("Next Month", f"${self.metrics['projections']['next_month']:,}")
            table.add_row("3 Months", f"${self.metrics['projections']['3_months']:,}")
            table.add_row("6 Months", f"${self.metrics['projections']['6_months']:,}")
            table.add_row("1 Year", f"${self.metrics['projections']['1_year']:,}")

        # Path to targets
        table.add_row("", "")  # Spacer
        table.add_row("[bold]Path to Targets[/bold]", "")
        table.add_row("To $5K MRR", f"Need {self.metrics.get('subs_for_5k', 0)} subs")
        table.add_row("To $10K MRR", f"Need {self.metrics.get('subs_for_10k', 0)} subs")
        table.add_row("To $50K MRR", f"Need {self.metrics.get('subs_for_50k', 0)} subs")

        # Top newsletters
        if "newsletters" in self.metrics and self.metrics["newsletters"]:
            table.add_row("", "")  # Spacer
            table.add_row("[bold]Top Newsletters[/bold]", "")

            sorted_newsletters = sorted(
                self.metrics["newsletters"],
                key=lambda x: x["mrr"],
                reverse=True
            )[:3]

            for nl in sorted_newsletters:
                table.add_row(
                    nl["name"][:30],
                    f"${nl['mrr']:,}/mo ({nl['subscribers']} subs)"
                )

        return Panel(table, border_style="green")

    def create_operations_panel(self):
        """Create operations metrics panel."""
        table = Table(title="⚔️ Operations Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Operation", style="cyan", no_wrap=True)
        table.add_column("Status", style="yellow")

        # Content operations
        content_ops = self.metrics.get("content_ops", {})
        table.add_row("[bold]Content Army[/bold]", "")
        table.add_row("Feeds Processed", str(content_ops.get("feeds_processed", 0)))
        table.add_row("Articles Fetched", str(content_ops.get("articles_fetched", 0)))
        table.add_row("Articles Summarized", str(content_ops.get("articles_summarized", 0)))
        table.add_row("Newsletters Generated", str(content_ops.get("newsletters_generated", 0)))
        table.add_row("Emails Sent", str(content_ops.get("emails_sent", 0)))

        # Revenue operations
        revenue_ops = self.metrics.get("revenue_ops", {})
        table.add_row("", "")  # Spacer
        table.add_row("[bold]Revenue Battalion[/bold]", "")
        table.add_row("Prospects Found", str(revenue_ops.get("prospects_found", 0)))
        table.add_row("Outreach Sent", str(revenue_ops.get("outreach_sent", 0)))
        table.add_row("Trials Started", str(revenue_ops.get("trials_started", 0)))
        table.add_row("Conversions", str(revenue_ops.get("conversions", 0)))
        table.add_row("MRR Added", f"${revenue_ops.get('mrr_added', 0)}")

        # System status
        table.add_row("", "")  # Spacer
        table.add_row("[bold]System Status[/bold]", "")
        table.add_row("Database", "[green]✓ Connected[/green]")
        table.add_row("Ollama", "[green]✓ Ready[/green]" if self.check_ollama() else "[red]✗ Offline[/red]")
        table.add_row("SMTP", "[green]✓ Configured[/green]" if settings.smtp_user else "[yellow]⚠ Not configured[/yellow]")

        return Panel(table, border_style="blue")

    def create_footer(self):
        """Create footer panel."""
        commands = (
            "[bold]Commands:[/bold] "
            "[yellow]q[/yellow]=quit | "
            "[yellow]r[/yellow]=refresh | "
            "[yellow]c[/yellow]=run content army | "
            "[yellow]s[/yellow]=run sales battalion"
        )

        status = "[green]● OPERATIONAL[/green]" if self.metrics.get("total_mrr", 0) > 0 else "[yellow]● LAUNCHING[/yellow]"

        return Panel(
            f"{commands} | Status: {status}",
            style="dim white on black"
        )

    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import requests
            response = requests.get(f"{settings.ollama_host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False


async def main():
    """Main dashboard function."""
    dashboard = BattleDashboard()

    console.print("[bold green]Starting Battle Dashboard...[/bold green]\n")

    # Start monitoring
    await dashboard.start_monitoring()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard shutdown complete.[/yellow]")