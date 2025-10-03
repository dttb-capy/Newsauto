"""Default high-quality content sources for newsletters."""

DEFAULT_SOURCES = {
    "AI & Machine Learning": [
        {
            "name": "OpenAI Blog",
            "type": "rss",
            "url": "https://openai.com/blog/rss.xml",
            "config": {"parse_full_text": True},
        },
        {
            "name": "DeepMind Blog",
            "type": "rss",
            "url": "https://deepmind.com/blog/feed/basic/",
            "config": {"parse_full_text": True},
        },
        {
            "name": "GitHub AI Trending",
            "type": "github",
            "url": "",
            "config": {"language": "", "since": "weekly", "limit": 10},
        },
        {
            "name": "Dev.to AI",
            "type": "devto",
            "url": "",
            "config": {"tag": "ai", "min_reactions": 20, "limit": 10},
        },
        {
            "name": "HackerNews AI",
            "type": "hackernews",
            "url": "",
            "config": {"story_type": "top", "min_score": 100, "limit": 20},
        },
    ],
    "System Design & Architecture": [
        {
            "name": "High Scalability",
            "type": "rss",
            "url": "http://feeds.feedburner.com/HighScalability",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Netflix Tech Blog",
            "type": "rss",
            "url": "https://netflixtechblog.com/feed",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Uber Engineering",
            "type": "rss",
            "url": "https://eng.uber.com/feed/",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Stripe Engineering",
            "type": "rss",
            "url": "https://stripe.com/blog/feed.rss",
            "config": {
                "parse_full_text": True,
                "keywords": ["engineering", "infrastructure"],
            },
        },
        {
            "name": "GitHub Systems Trending",
            "type": "github",
            "url": "",
            "config": {"language": "go", "since": "weekly", "limit": 10},
        },
    ],
    "DevOps & Cloud": [
        {
            "name": "AWS Blog",
            "type": "rss",
            "url": "https://aws.amazon.com/blogs/devops/feed/",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Google Cloud Blog",
            "type": "rss",
            "url": "https://cloud.google.com/feeds/devops-release-notes.xml",
            "config": {"parse_full_text": True},
        },
        {
            "name": "HashiCorp Blog",
            "type": "rss",
            "url": "https://www.hashicorp.com/blog/feed.xml",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Dev.to DevOps",
            "type": "devto",
            "url": "",
            "config": {"tag": "devops", "min_reactions": 15, "limit": 10},
        },
        {
            "name": "GitHub DevOps Tools",
            "type": "github",
            "url": "",
            "config": {"language": "", "since": "weekly", "limit": 10},
        },
    ],
    "Web Development": [
        {
            "name": "CSS Tricks",
            "type": "rss",
            "url": "https://css-tricks.com/feed/",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Smashing Magazine",
            "type": "rss",
            "url": "https://www.smashingmagazine.com/feed/",
            "config": {"parse_full_text": True},
        },
        {
            "name": "Dev.to JavaScript",
            "type": "devto",
            "url": "",
            "config": {"tag": "javascript", "min_reactions": 25, "limit": 15},
        },
        {
            "name": "GitHub JavaScript Trending",
            "type": "github",
            "url": "",
            "config": {"language": "javascript", "since": "daily", "limit": 10},
        },
        {
            "name": "HackerNews Web",
            "type": "hackernews",
            "url": "",
            "config": {"story_type": "top", "min_score": 50, "limit": 15},
        },
    ],
    "General Tech": [
        {
            "name": "TechCrunch",
            "type": "rss",
            "url": "https://techcrunch.com/feed/",
            "config": {"parse_full_text": False, "limit": 10},
        },
        {
            "name": "The Verge",
            "type": "rss",
            "url": "https://www.theverge.com/rss/index.xml",
            "config": {"parse_full_text": False, "limit": 10},
        },
        {
            "name": "Ars Technica",
            "type": "rss",
            "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "config": {"parse_full_text": True},
        },
        {
            "name": "HackerNews Top",
            "type": "hackernews",
            "url": "",
            "config": {"story_type": "best", "min_score": 200, "limit": 25},
        },
        {
            "name": "Dev.to Top",
            "type": "devto",
            "url": "",
            "config": {"tag": "", "min_reactions": 50, "limit": 20},
        },
        {
            "name": "GitHub All Languages",
            "type": "github",
            "url": "",
            "config": {"language": "", "since": "daily", "limit": 15},
        },
    ],
}


def get_sources_for_niche(niche: str) -> list:
    """Get recommended sources for a specific niche.

    Args:
        niche: Newsletter niche/category

    Returns:
        List of source configurations
    """
    # Try exact match first
    if niche in DEFAULT_SOURCES:
        return DEFAULT_SOURCES[niche]

    # Try partial match
    niche_lower = niche.lower()
    for key, sources in DEFAULT_SOURCES.items():
        if niche_lower in key.lower() or key.lower() in niche_lower:
            return sources

    # Default to general tech if no match
    return DEFAULT_SOURCES.get("General Tech", [])
