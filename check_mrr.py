#!/usr/bin/env python3
"""
Quick MRR checker for Newsauto
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber, NewsletterSubscriber
from rich.console import Console
from rich.table import Table

console = Console()
settings = get_settings()


def check_mrr():
    """Check current MRR and display dashboard."""
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all newsletters
        newsletters = session.query(Newsletter).all()

        # Create table
        table = Table(title="🚀 NEWSAUTO MRR DASHBOARD", show_header=True, header_style="bold magenta")
        table.add_column("Newsletter", style="cyan", width=40)
        table.add_column("Price", style="green", justify="right")
        table.add_column("Subscribers", style="yellow", justify="right")
        table.add_column("MRR", style="bold green", justify="right")

        total_mrr = 0
        total_subs = 0

        for newsletter in newsletters:
            price = newsletter.settings.get("price_monthly", 0)
            if price > 0:  # Only show premium newsletters
                mrr = newsletter.subscriber_count * price
                total_mrr += mrr
                total_subs += newsletter.subscriber_count

                table.add_row(
                    newsletter.name[:40],
                    f"${price}",
                    str(newsletter.subscriber_count),
                    f"${mrr}"
                )

        console.print(table)

        # Summary
        console.print("\n" + "="*60)
        console.print(f"[bold cyan]TOTAL SUBSCRIBERS:[/bold cyan] {total_subs}")
        console.print(f"[bold green]TOTAL MRR:[/bold green] ${total_mrr:,}")

        # Path to targets
        if total_mrr < 5000:
            needed = 5000 - total_mrr
            avg_price = 45
            subs_needed = int(needed / avg_price)
            console.print(f"[yellow]Path to $5K MRR:[/yellow] Need {subs_needed} more subscribers")
        else:
            console.print(f"[bold green]🎉 TARGET ACHIEVED! ${total_mrr:,} MRR![/bold green]")

        console.print("="*60)

        # Growth projections
        console.print("\n[bold]GROWTH PROJECTIONS:[/bold]")
        console.print(f"Month 1: ${total_mrr * 5:,} (with marketing)")
        console.print(f"Month 2: ${total_mrr * 20:,} (with automation)")
        console.print(f"Month 3: ${total_mrr * 50:,} (with scale)")

    finally:
        session.close()


if __name__ == "__main__":
    check_mrr()