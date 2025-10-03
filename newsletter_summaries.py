#!/usr/bin/env python3
"""
Display one-paragraph summaries of all 10 premium newsletters
"""

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

console = Console()

NEWSLETTER_SUMMARIES = {
    "1. CTO/VP Engineering Playbook - $50/mo":
        "Strategic weekly insights for CTOs and VPs scaling engineering teams from 50 to 500 engineers. "
        "Delivers battle-tested strategies from Stripe, Uber, and Netflix on team scaling, technical debt management, "
        "engineering velocity optimization, and board reporting. Each issue includes implementation timelines, resource "
        "requirements, and common pitfalls at scale, specifically tailored for $10M-100M ARR companies facing rapid growth challenges.",

    "2. Family Office Tech Insights - $150/mo":
        "Exclusive technology investment intelligence for family offices and ultra-high-net-worth individuals managing "
        "$100M+ portfolios. Covers direct investment opportunities in deep tech, due diligence frameworks, portfolio "
        "allocation strategies (typically 10-20% in tech), and co-investment opportunities with notable family offices. "
        "Reveals where Bezos, Gates, and Thiel are deploying personal wealth with valuation multiples and exit strategies.",

    "3. B2B SaaS Founder Intelligence - $40/mo":
        "Weekly playbook for B2B SaaS founders scaling from $1M to $100M ARR, featuring real metrics and tactics from "
        "monday.com, Notion, and Linear's growth journeys. Covers product-market fit indicators, ARR growth hacks, "
        "churn reduction strategies, PLG implementation, and fundraising benchmarks. Includes specific SaaS metrics "
        "(CAC, LTV, Magic Number, Rule of 40) with actionable timelines and resource requirements.",

    "4. Veteran Executive Network - $50/mo":
        "Elite network intelligence for veteran CEOs, CTOs, and board members transitioning from military to C-suite roles. "
        "Showcases how veterans built Palantir, Anduril, and other billion-dollar companies while translating military "
        "leadership principles to business success. Covers veteran-specific advantages (VOSB/SDVOSB certifications), "
        "$2B VA tech modernization opportunities, and Fortune 500 veteran hiring initiatives with 2.3x higher success rates.",

    "5. LatAm Tech Talent Pipeline - $45/mo":
        "Strategic guide for US CTOs and VP Engineering hiring elite Latin American developers to save 60% on engineering "
        "costs while maintaining quality. Covers timezone advantages (1-3 hour difference), cultural alignment, English "
        "proficiency standards, and legal/tax frameworks across 12 LatAm countries. Features salary benchmarks "
        "($60k vs $200k domestically) and case studies from SF startups building entire teams in São Paulo and Buenos Aires.",

    "6. Defense Tech Innovation - $35/mo":
        "DoD procurement intelligence for defense contractors and startups targeting the Pentagon's $280B modernization budget. "
        "Covers SBIR/STTR opportunities, dual-use technology requirements, JADC2 integration contracts ($30B available), "
        "and success patterns from Anduril and Palantir. Includes China tech restrictions creating $50B domestic opportunities "
        "and veteran-owned business advantages in defense contracting.",

    "7. Principal Engineer Career - $30/mo":
        "Career acceleration guide for Senior and Staff engineers targeting Principal/Distinguished roles with $400K-600K+ "
        "compensation at FAANG companies. Features real Principal Engineer interview questions, promotion packet strategies, "
        "scope and impact expectations at L7+/E7+ levels, and compensation negotiation data points. Includes system design "
        "mastery techniques and strategies for building influence without authority.",

    "8. Faith-Based Enterprise Tech - $25/mo":
        "Digital transformation insights for CTOs/CIOs at faith-based organizations, megachurches, and religious universities "
        "serving 500+ members. Shows how Life.Church and Hillsong scale to millions with technology while respecting tradition. "
        "Covers online giving optimization (30-50% increase typical), livestreaming solutions, community platform selection, "
        "and hybrid worship technologies with real implementation case studies.",

    "9. No-Code Agency Empire - $35/mo":
        "Scaling playbook for agency owners and freelancers building $1M+ agencies with Webflow, Bubble, and Framer. "
        "Features client acquisition strategies (CAC $500-2000), pricing models achieving 50-70% margins, recurring "
        "revenue transformation, and the journey from freelancer to team. Includes real examples of agencies charging "
        "$100k for 2-week MVPs and reaching $50k/month with 3-person teams.",

    "10. Tech Succession Planning - $40/mo":
        "Modernization guide for family business owners and second-generation leaders preparing $10M+ revenue businesses "
        "for digital transformation and succession. Bridges generational gaps in technology adoption while preserving "
        "family values and legacy. Covers how succession planning affects M&A valuations, with 73% of tech companies "
        "lacking plans seeing 23% value drops at founder departure."
}

def display_summaries():
    """Display newsletter summaries in a formatted way."""

    console.print("\n[bold cyan]📰 10 PREMIUM NEWSLETTER SUMMARIES[/bold cyan]")
    console.print("[yellow]Each targeting high-value C-suite and elite technical audiences[/yellow]\n")
    console.print("="*80 + "\n")

    for title, summary in NEWSLETTER_SUMMARIES.items():
        # Create a panel for each newsletter
        panel = Panel(
            summary,
            title=f"[bold green]{title}[/bold green]",
            border_style="blue",
            padding=(1, 2),
            expand=False
        )
        console.print(panel)
        console.print()

    # Revenue summary
    console.print("="*80)
    console.print("\n[bold yellow]💰 REVENUE MODEL[/bold yellow]")
    console.print("[green]With 146 subscribers per newsletter (Portuguese Model):[/green]")
    console.print("• Total Monthly Revenue: [bold]$73,000[/bold]")
    console.print("• Operating Costs: [bold]$10[/bold]")
    console.print("• Net Profit: [bold]$72,990[/bold] (99.98% margin)")
    console.print("\n[bold cyan]Current Status: $6,075 MRR with 100 subscribers[/bold cyan]")
    console.print("="*80)

if __name__ == "__main__":
    display_summaries()