#!/usr/bin/env python
"""
Generate a preview newsletter HTML file that can be viewed in a browser.
Demonstrates the 10-niche automated newsletter system.
"""

from datetime import datetime
from jinja2 import Template
import webbrowser
import os

def generate_preview_newsletter():
    """Generate a sample newsletter for the CTO/VP Engineering Playbook niche."""

    print("=" * 70)
    print("📰 GENERATING PREVIEW NEWSLETTER")
    print("=" * 70)

    # Sample data for the CTO/VP Engineering Playbook newsletter
    newsletter_data = {
        "newsletter": {
            "name": "CTO/VP Engineering Playbook",
            "value_proposition": "Strategic insights for engineering leaders at Series A-D startups"
        },
        "edition": "Executive Edition",
        "current_date": datetime.now(),
        "dateformat": datetime.now().strftime("%B %d, %Y"),

        # Executive Summary - 3 key takeaways
        "executive_takeaways": [
            "OpenAI's new o3 model achieves 25% cost reduction while maintaining GPT-4 performance - immediate infrastructure savings opportunity",
            "Google's engineering team restructure shows 40% productivity gain with pod-based architecture - consider for Q1 2025 reorg",
            "Stripe's new hiring framework reduces time-to-productivity by 6 weeks - actionable template included"
        ],

        # Strategic Insights
        "strategic_insights": [
            {
                "title": "Rethinking Engineering Team Structure for 2025",
                "impact": "High Impact",
                "timeframe": "Q1 2025",
                "source": "Stripe Engineering Blog",
                "summary": "Stripe's engineering organization has pioneered a new 'pod' structure that increased deployment velocity by 40% while reducing cross-team dependencies. The model focuses on 6-8 person autonomous units with embedded product and design resources. Early adopters report 25% reduction in meeting overhead and 2x faster feature delivery.",
                "metrics": [
                    {"value": "40%", "label": "Deployment Velocity", "change": 40},
                    {"value": "6-8", "label": "Optimal Pod Size", "change": 0},
                    {"value": "2x", "label": "Feature Speed", "change": 100}
                ],
                "action_required": True,
                "url": "#"
            },
            {
                "title": "AI Infrastructure Costs: The Hidden Optimization Opportunity",
                "impact": "Financial Impact",
                "timeframe": "Immediate",
                "source": "OpenAI Research",
                "summary": "New analysis reveals that 73% of companies are overspending on AI infrastructure by not implementing proper caching and batching strategies. Simple optimizations like prompt caching and batch inference can reduce costs by 60% without performance degradation. OpenAI's new pricing model rewards efficient API usage with volume discounts up to 50%.",
                "metrics": [
                    {"value": "$385K", "label": "Avg Annual Savings", "change": -60},
                    {"value": "73%", "label": "Companies Overspending", "change": 0},
                    {"value": "2.3ms", "label": "Latency Impact", "change": 5}
                ],
                "action_required": True,
                "url": "#"
            },
            {
                "title": "The Great Senior Engineer Shortage: Retention Strategies That Work",
                "impact": "Talent Crisis",
                "timeframe": "Q1-Q2 2025",
                "source": "LinkedIn Engineering Talent Report",
                "summary": "With 89% of senior engineers open to new opportunities, retention has become critical. Companies implementing 'technical career ladders' to Staff/Principal levels see 45% better retention. The key: clearly defined technical leadership roles that don't require people management. Netflix and Uber's models show highest success rates.",
                "metrics": [
                    {"value": "89%", "label": "Engineers Open to Move", "change": 12},
                    {"value": "45%", "label": "Better Retention", "change": 45},
                    {"value": "$180K", "label": "Replacement Cost", "change": 20}
                ],
                "action_required": False,
                "url": "#"
            }
        ],

        # Market Intelligence
        "market_intelligence": [
            {
                "headline": "Microsoft's $10B Investment in AI Infrastructure Sets New Competitive Bar",
                "analysis": "Microsoft's massive infrastructure investment signals a shift in competitive dynamics. Companies without similar AI capabilities risk being left behind in product innovation cycles. The investment includes dedicated GPU clusters for enterprise customers, potentially disrupting AWS and GCP's dominance.",
                "competitive_impact": "Action Required: Evaluate current AI infrastructure strategy. Consider partnerships vs. build decisions. Microsoft's move may trigger pricing wars in cloud AI services, creating opportunity for strategic negotiations."
            },
            {
                "headline": "YCombinator Reports 60% of New Startups Are AI-First",
                "analysis": "The latest YC batch shows a dramatic shift toward AI-native architectures. These startups are building with 70% less code and reaching MVP 3x faster than traditional approaches. This represents both opportunity and threat for established companies.",
                "competitive_impact": "Strategic Consideration: AI-first startups may disrupt your market faster than anticipated. Consider acquiring or partnering with promising teams before competitors do."
            }
        ],

        # Recommended Actions
        "recommended_actions": [
            {
                "text": "Schedule engineering org review to evaluate pod-based team structure",
                "deadline": "Jan 15, 2025"
            },
            {
                "text": "Audit current AI/ML infrastructure costs and identify optimization opportunities",
                "deadline": "Jan 10, 2025"
            },
            {
                "text": "Review senior engineer retention metrics and compensation benchmarks",
                "deadline": "Jan 20, 2025"
            },
            {
                "text": "Evaluate technical career ladder implementation for Staff/Principal roles",
                "deadline": "Feb 1, 2025"
            }
        ],

        # Thought Leader Quote
        "thought_leader_quote": {
            "text": "The best engineering leaders are not those who have all the answers, but those who create environments where the right questions get asked and solved autonomously.",
            "author": "Will Larson",
            "title": "CTO at Carta, Author of 'An Elegant Puzzle'"
        },

        # Premium CTA
        "premium_cta": {
            "headline": "Join 146 Engineering Leaders Already Subscribed",
            "subheading": "Get weekly strategic insights tailored for CTOs and VPs of Engineering at high-growth startups",
            "button_text": "Upgrade to Premium ($50/month)",
            "url": "#"
        },

        # Subscriber info
        "subscriber_tier": "PREMIUM SUBSCRIBER",
        "subscriber_value": "$50/month • Full Access",
        "subscriber_company": "Your Company",

        # Links
        "dashboard_url": "#dashboard",
        "preferences_url": "#preferences",
        "refer_url": "#refer",
        "unsubscribe_url": "#unsubscribe",
        "tracking_pixel": None
    }

    # Read the executive newsletter template
    template_path = "newsauto/templates/executive_newsletter.html"
    with open(template_path, 'r') as f:
        template_content = f.read()

    # Add a simple dateformat filter
    def dateformat(value):
        if isinstance(value, datetime):
            return value.strftime("%B %d, %Y")
        return value

    # Render the template
    template = Template(template_content)
    template.globals['dateformat'] = dateformat

    # Add default filter
    def default_filter(value, default_value):
        return value if value else default_value
    template.globals['default'] = default_filter

    html_content = template.render(**newsletter_data)

    # Save to file
    output_file = "preview_newsletter.html"
    with open(output_file, 'w') as f:
        f.write(html_content)

    print(f"\n✅ Newsletter preview generated: {output_file}")

    # Get absolute path
    abs_path = os.path.abspath(output_file)
    print(f"\n📂 File location: {abs_path}")
    print(f"\n🌐 To view in browser:")
    print(f"   1. Open your web browser")
    print(f"   2. Navigate to: file://{abs_path}")
    print(f"   Or simply double-click the file in your file manager")

    # Try to open in default browser
    try:
        webbrowser.open(f"file://{abs_path}")
        print(f"\n✨ Opening in your default browser...")
    except:
        print(f"\n💡 Couldn't auto-open browser. Please open manually.")

    print("\n" + "=" * 70)
    print("📊 NEWSLETTER FEATURES DEMONSTRATED:")
    print("-" * 50)
    print("✅ Executive Summary with 3 key takeaways")
    print("✅ Strategic Insights with metrics and actions")
    print("✅ Market Intelligence with competitive analysis")
    print("✅ Recommended Actions with deadlines")
    print("✅ Thought Leadership quotes")
    print("✅ Premium CTAs and subscription tiers")
    print("✅ Professional executive design")
    print("\n💰 This newsletter targets: $50/month per subscriber")
    print("   146 subscribers = $7,300/month from this niche alone")
    print("   With all 10 niches: ~$50,000/month potential")

    return abs_path

if __name__ == "__main__":
    generate_preview_newsletter()