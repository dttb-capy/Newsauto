#!/usr/bin/env python3
"""
View Episode 1 content for a specific newsletter or all newsletters
"""

import sys
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def view_episode(newsletter_name=None):
    """View Episode 1 content."""

    # Load Episode 1 content
    with open("episode_1_content.json", "r") as f:
        episodes = json.load(f)

    if newsletter_name:
        # Show specific newsletter
        if newsletter_name in episodes:
            display_newsletter_episode(newsletter_name, episodes[newsletter_name])
        else:
            console.print(f"[red]Newsletter '{newsletter_name}' not found[/red]")
            console.print("\nAvailable newsletters:")
            for name in episodes.keys():
                console.print(f"  • {name}")
    else:
        # Show menu
        console.print("[bold cyan]📰 EPISODE 1 - PREMIUM NEWSLETTERS[/bold cyan]\n")
        console.print("Select a newsletter to view:\n")

        for i, (name, content) in enumerate(episodes.items(), 1):
            price = {
                "CTO/VP Engineering Playbook": "$50",
                "Family Office Tech Insights": "$150",
                "B2B SaaS Founder Intelligence": "$40",
                "Veteran Executive Network": "$50",
                "LatAm Tech Talent Pipeline": "$45",
                "Defense Tech Innovation Digest": "$35",
                "Principal Engineer Career Accelerator": "$30",
                "Faith-Based Enterprise Tech": "$25",
                "No-Code Agency Empire": "$35",
                "Tech Succession Planning": "$40"
            }.get(name, "$0")

            console.print(f"[bold]{i}.[/bold] {name} [green]({price}/mo)[/green]")
            console.print(f"   [dim]{content['subject']}[/dim]\n")


def display_newsletter_episode(name, content):
    """Display a single newsletter episode."""

    console.print("\n" + "="*80)
    console.print(f"[bold cyan]{name}[/bold cyan]")
    console.print("="*80 + "\n")

    # Subject line
    console.print(Panel(
        content['subject'],
        title="[bold]Episode 1 Subject Line[/bold]",
        border_style="green"
    ))

    # Executive Summary
    console.print("\n[bold yellow]📋 EXECUTIVE SUMMARY[/bold yellow]")
    for point in content['executive_summary']:
        console.print(f"  • {point}")

    # Main Insights
    console.print("\n[bold yellow]💡 KEY INSIGHTS[/bold yellow]\n")
    for i, insight in enumerate(content['main_insights'], 1):
        panel_content = f"[bold]{insight['content']}[/bold]\n\n"
        panel_content += f"[green]→ Action:[/green] {insight['action']}\n"
        panel_content += f"[cyan]📊 Metric:[/cyan] {insight['metric']}"

        console.print(Panel(
            panel_content,
            title=f"[bold]{i}. {insight['title']}[/bold]",
            border_style="blue"
        ))

    # Key Metrics/Data
    metrics_key = next(
        (k for k in ['key_metrics', 'portfolio_breakdown', 'growth_metrics',
         'cost_comparison', 'veteran_advantages', 'contract_vehicles',
         'level_comparison', 'tech_stack', 'revenue_ladder',
         'modernization_priorities']
         if k in content),
        None
    )

    if metrics_key:
        console.print(f"\n[bold yellow]📊 {metrics_key.upper().replace('_', ' ')}[/bold yellow]")
        for key, value in content[metrics_key].items():
            formatted_key = key.replace('_', ' ').title()
            console.print(f"  • [cyan]{formatted_key}:[/cyan] {value}")

    console.print("\n" + "="*80)
    console.print("[dim]This is Episode 1 of your premium newsletter subscription[/dim]")
    console.print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # View specific newsletter
        newsletter = " ".join(sys.argv[1:])
        view_episode(newsletter)
    else:
        # Show menu
        view_episode()

        # Interactive selection
        console.print("\n[bold]Enter newsletter number to view (1-10) or 'q' to quit:[/bold] ", end="")
        choice = input()

        if choice.lower() != 'q' and choice.isdigit():
            newsletters = list(json.load(open("episode_1_content.json")).keys())
            idx = int(choice) - 1
            if 0 <= idx < len(newsletters):
                console.clear()
                view_episode(newsletters[idx])