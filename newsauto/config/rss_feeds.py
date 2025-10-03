"""
RSS feed configuration for premium newsletter niches.
Maps each niche to curated high-quality RSS feeds for content aggregation.
"""

from typing import Dict, List

# RSS feed mappings for each niche
NICHE_RSS_FEEDS: Dict[str, List[str]] = {
    "cto_engineering_playbook": [
        # Engineering leadership
        "https://martinfowler.com/feed.atom",
        "https://www.highscalability.com/rss.xml",
        "https://engineering.atspotify.com/feed/",
        "https://netflixtechblog.com/feed",
        "https://eng.uber.com/feed/",
        "https://aws.amazon.com/blogs/architecture/feed/",
        "https://cloud.google.com/feeds/kubernetes-engine-release-notes.xml",
        "https://github.blog/engineering.atom",
        "https://stackoverflow.blog/feed/",
        "https://www.infoq.com/feed",
    ],

    "b2b_saas_founder": [
        # SaaS and startup focused
        "https://www.saastr.com/feed/",
        "https://tomtunguz.com/index.xml",
        "https://a16z.com/feed/",
        "https://firstround.com/review/feed.xml",
        "https://blog.ycombinator.com/feed/",
        "https://www.forentrepreneurs.com/feed/",
        "https://www.groovehq.com/blog/rss.xml",
        "https://blog.hubspot.com/rss.xml",
        "https://www.profitwell.com/customer-churn/feed",
        "https://baremetrics.com/blog/feed",
    ],

    "principal_engineer_career": [
        # Senior engineering career development
        "https://staffeng.com/rss.xml",
        "https://leaddev.com/rss.xml",
        "https://www.swyx.io/rss.xml",
        "https://charity.wtf/feed/",
        "https://lethain.com/feeds/posts/",
        "https://blog.pragmaticengineer.com/rss/",
        "https://newsletter.pragmaticengineer.com/feed",
        "https://danluu.com/atom.xml",
        "https://jvns.ca/atom.xml",
        "https://www.kitchensoap.com/feed/",
    ],

    "defense_tech_innovation": [
        # Defense and government tech
        "https://www.c4isrnet.com/arc/outboundfeeds/rss/",
        "https://www.defensenews.com/arc/outboundfeeds/rss/",
        "https://www.fedscoop.com/feed/",
        "https://www.nextgov.com/rss/",
        "https://www.defenseone.com/rss/",
        "https://www.anduril.com/feed.xml",
        "https://shield.ai/feed/",
        "https://blog.palantir.com/feed",
        "https://www.diu.mil/latest-rss",
        "https://www.darpa.mil/rss",
    ],

    "veteran_executive_network": [
        # Veteran and military transition
        "https://taskandpurpose.com/feed/",
        "https://www.military.com/rss-feeds/content",
        "https://ivmf.syracuse.edu/feed/",
        "https://www.hiringourheroes.org/feed/",
        "https://www.linkedin.com/pulse/rss/",  # Will filter for veteran content
        "https://www.veteranownedbusiness.com/feed/",
        "https://www.militarytimes.com/arc/outboundfeeds/rss/",
        "https://bunkerconnect.com/feed/",
        "https://www.rallypoint.com/answers.rss",
    ],

    "latam_tech_talent": [
        # Latin American tech ecosystem
        "https://latamlist.com/feed/",
        "https://contxto.com/en/feed/",
        "https://labsnews.com/en/feed/",
        "https://restofworld.org/feed/",  # Filter for LatAm content
        "https://www.techinbrazil.com/feed/",
        "https://startupi.com.br/feed/",
        "https://www.startupgrind.com/blog/feed/",  # Filter for LatAm
        "https://500.co/feed/",  # Filter for LatAm portfolio
        "https://techcrunch.com/category/startups/feed/",  # Filter for LatAm
    ],

    "faith_based_enterprise": [
        # Faith-based business and tech
        "https://www.christianitytoday.com/ct/feeds/",
        "https://relevantmagazine.com/feed/",
        "https://www.faithdrivenentrepreneur.org/feed",
        "https://www.praxislabs.org/feed",
        "https://www.faith-driven-investor.org/feed",
        "https://www.patheos.com/blogs/faithandwork/feed",
        "https://theologyofwork.org/feed",
        "https://www.ethicsandculture.com/blog?format=rss",
    ],

    "family_office_tech": [
        # Wealth management and family office
        "https://www.wealthmanagement.com/rss.xml",
        "https://www.fa-mag.com/rss/",
        "https://www.institutionalinvestor.com/feed",
        "https://www.ai-cio.com/feed/",
        "https://www.privatebankerinternational.com/feed/",
        "https://www.wsj.com/xml/rss/3_7031.xml",  # WSJ Wealth
        "https://www.ft.com/wealth?format=rss",
        "https://www.forbes.com/investing/feed/",
        "https://www.barrons.com/xml/rss/3_7510.xml",
    ],

    "no_code_agency": [
        # No-code and automation
        "https://www.nocode.tech/feed",
        "https://www.makerpad.co/feed",
        "https://www.zapier.com/blog/feeds/latest/",
        "https://webflow.com/blog/feed",
        "https://bubble.io/blog/rss/",
        "https://www.airtable.com/blog/rss",
        "https://www.notion.so/blog/feed",
        "https://retool.com/blog/rss.xml",
        "https://n8n.io/blog/rss.xml",
        "https://www.make.com/en/blog.rss",
    ],

    "tech_succession_planning": [
        # Business succession and transition
        "https://www.familybusinessmagazine.com/feed",
        "https://www.bizbuysell.com/news/feed/",
        "https://www.exitplanning.com/feed/",
        "https://www.acquisition.biz/feed/",
        "https://www.axial.net/feed/",
        "https://www.businesstransition.com/feed/",
        "https://www.successionplanning.com/feed/",
        "https://hbr.org/topic/succession-planning.rss",
        "https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/rss",
    ],
}

# Fallback general tech feeds (used when niche feeds are unavailable)
GENERAL_TECH_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://techcrunch.com/feed/",
    "https://www.techmeme.com/feed.xml",
    "https://www.theverge.com/rss/index.xml",
    "https://arstechnica.com/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
]

# Premium/paid feed sources that require API keys (stored in env vars)
PREMIUM_FEEDS = {
    "bloomberg": {
        "base_url": "https://www.bloomberg.com/professional/feed/",
        "env_key": "BLOOMBERG_API_KEY",
        "niches": ["family_office_tech", "tech_succession_planning"],
    },
    "gartner": {
        "base_url": "https://www.gartner.com/en/feed",
        "env_key": "GARTNER_API_KEY",
        "niches": ["cto_engineering_playbook", "defense_tech_innovation"],
    },
    "forrester": {
        "base_url": "https://www.forrester.com/feed",
        "env_key": "FORRESTER_API_KEY",
        "niches": ["b2b_saas_founder", "principal_engineer_career"],
    },
}


def get_feeds_for_niche(niche_key: str, include_general: bool = False) -> List[str]:
    """
    Get RSS feeds for a specific niche.

    Args:
        niche_key: The niche identifier
        include_general: Whether to include general tech feeds as fallback

    Returns:
        List of RSS feed URLs
    """
    feeds = NICHE_RSS_FEEDS.get(niche_key, [])

    if include_general or not feeds:
        feeds.extend(GENERAL_TECH_FEEDS)

    # Remove duplicates while preserving order
    seen = set()
    unique_feeds = []
    for feed in feeds:
        if feed not in seen:
            seen.add(feed)
            unique_feeds.append(feed)

    return unique_feeds


def get_all_unique_feeds() -> List[str]:
    """Get all unique RSS feeds across all niches."""
    all_feeds = set()
    for feeds in NICHE_RSS_FEEDS.values():
        all_feeds.update(feeds)
    all_feeds.update(GENERAL_TECH_FEEDS)
    return sorted(list(all_feeds))


def validate_feeds() -> Dict[str, List[str]]:
    """
    Validate that all niches have at least some RSS feeds.

    Returns:
        Dictionary of niches with missing or insufficient feeds
    """
    issues = {}
    for niche, feeds in NICHE_RSS_FEEDS.items():
        if not feeds:
            issues[niche] = ["No feeds configured"]
        elif len(feeds) < 3:
            issues[niche] = [f"Only {len(feeds)} feeds configured (recommend at least 3)"]
    return issues


# Export convenience
__all__ = [
    "NICHE_RSS_FEEDS",
    "GENERAL_TECH_FEEDS",
    "PREMIUM_FEEDS",
    "get_feeds_for_niche",
    "get_all_unique_feeds",
    "validate_feeds",
]