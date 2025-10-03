"""
Newsletter niche configurations based on profitable market analysis.
Each niche includes targeting, content sources, prompts, and monetization strategies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class NicheCategory(Enum):
    """Categories of newsletter niches."""

    ENGINEERING = "engineering"
    SECURITY = "security"
    DATA = "data"
    CLOUD = "cloud"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    DEVOPS = "devops"
    AI_ML = "ai_ml"
    CAREER = "career"
    BUSINESS = "business"


@dataclass
class ContentSource:
    """Content source configuration."""

    name: str
    url: str
    type: str  # rss, api, scraper
    priority: int = 1
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NicheConfig:
    """Complete configuration for a newsletter niche."""

    name: str
    category: NicheCategory
    description: str
    target_audience: str
    value_proposition: str

    # Content configuration
    content_sources: List[ContentSource]
    content_ratio: Dict[str, float]  # original, curated, syndicated percentages
    keywords: List[str]

    # AI/LLM configuration
    summarization_prompt: str
    curation_criteria: str
    tone_style: str

    # Newsletter configuration
    frequency: str  # daily, weekly, bi-weekly
    optimal_send_time: str  # e.g., "Tuesday 9AM EST"
    target_read_time: int  # in minutes

    # Monetization
    pricing_tiers: Dict[str, float]
    sponsorship_cpm: float  # cost per thousand impressions
    expected_conversion_rate: float

    # Engagement metrics targets
    target_open_rate: float
    target_click_rate: float
    target_share_rate: float

    # Template and formatting
    template_name: str

    # Optional fields with defaults
    exclude_keywords: List[str] = field(default_factory=list)
    enable_code_snippets: bool = False
    enable_diagrams: bool = False
    enable_metrics: bool = False


# Niche configurations
NEWSLETTER_NICHES: Dict[str, NicheConfig] = {
    "cto_engineering_playbook": NicheConfig(
        name="CTO/VP Engineering Playbook",
        category=NicheCategory.ENGINEERING,
        description="Strategic insights for CTOs and VPs scaling engineering teams",
        target_audience="CTOs, VPs Engineering, Engineering Directors at Series A-D startups",
        value_proposition="Scale from 50 to 500 engineers with battle-tested strategies from Stripe, Uber, and Netflix",
        content_sources=[
            ContentSource(
                "High Scalability",
                "http://feeds.feedburner.com/HighScalability",
                "rss",
                priority=1,
            ),
            ContentSource(
                "The Pragmatic Engineer",
                "https://blog.pragmaticengineer.com/rss/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "InfoQ Architecture",
                "https://www.infoq.com/architecture/rss/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "Martin Fowler", "https://martinfowler.com/feed.atom", "rss", priority=1
            ),
            ContentSource("CTO Craft", "https://ctocraft.com/feed/", "rss", priority=2),
        ],
        content_ratio={"original": 0.65, "curated": 0.25, "syndicated": 0.10},
        keywords=[
            "engineering leadership",
            "team scaling",
            "technical debt",
            "engineering velocity",
            "architecture decisions",
            "board reporting",
        ],
        exclude_keywords=["junior", "bootcamp", "tutorial"],
        summarization_prompt="""Summarize this content for CTOs and VPs of Engineering at growth-stage startups.
        Focus on: 1) Strategic implications for 50-500 person engineering orgs, 2) Implementation timeline and resource requirements,
        3) Board/investor communication angles, 4) Common pitfalls at scale.
        Frame insights in context of $10M-100M ARR companies.""",
        curation_criteria="Content must address engineering leadership challenges at scale (50+ engineers)",
        tone_style="Executive-level, strategic with emphasis on business impact and team dynamics",
        frequency="weekly",
        optimal_send_time="Tuesday 7AM EST",
        target_read_time=10,
        pricing_tiers={"free": 0, "pro": 50, "enterprise": 500},
        sponsorship_cpm=200,
        expected_conversion_rate=0.25,
        target_open_rate=0.48,
        target_click_rate=0.22,
        target_share_rate=0.12,
        template_name="executive_newsletter.html",
        enable_code_snippets=False,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "b2b_saas_founders": NicheConfig(
        name="B2B SaaS Founder Intelligence",
        category=NicheCategory.BUSINESS,
        description="Strategic insights for B2B SaaS founders scaling from $1M to $100M ARR",
        target_audience="B2B SaaS founders, CEOs, and founding teams at $1M-10M ARR",
        value_proposition="How monday.com, Notion, and Linear scaled to $100M+ ARR",
        content_sources=[
            ContentSource("SaaStr", "https://www.saastr.com/feed/", "rss", priority=1),
            ContentSource(
                "First Round Review",
                "http://feeds.firstround.com/firstround",
                "rss",
                priority=1,
            ),
            ContentSource(
                "OpenView Partners",
                "https://openviewpartners.com/feed/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "Tomasz Tunguz", "http://tomtunguz.com/index.xml", "rss", priority=1
            ),
            ContentSource(
                "ChartMogul", "https://blog.chartmogul.com/feed/", "rss", priority=2
            ),
        ],
        content_ratio={"original": 0.70, "curated": 0.20, "syndicated": 0.10},
        keywords=[
            "product-market fit",
            "ARR growth",
            "churn",
            "fundraising",
            "go-to-market",
            "PLG",
            "enterprise sales",
            "pricing strategy",
        ],
        exclude_keywords=["consumer", "B2C", "e-commerce"],
        summarization_prompt="""Summarize this content for B2B SaaS founders scaling from $1M to $10M ARR.
        Focus on: 1) Specific metrics and benchmarks, 2) Actionable tactics with timeline,
        3) Resource requirements (team size, burn rate), 4) Common pitfalls at this stage.
        Include relevant SaaS metrics (CAC, LTV, Magic Number, Rule of 40).""",
        curation_criteria="Must be relevant to B2B SaaS companies in growth stage ($1M-50M ARR)",
        tone_style="Direct, data-driven, founder-to-founder perspective",
        frequency="weekly",
        optimal_send_time="Wednesday 8AM EST",
        target_read_time=8,
        pricing_tiers={"free": 0, "pro": 40, "team": 300},
        sponsorship_cpm=175,
        expected_conversion_rate=0.20,
        target_open_rate=0.45,
        target_click_rate=0.20,
        target_share_rate=0.10,
        template_name="executive_newsletter.html",
        enable_code_snippets=False,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "principal_engineer_career": NicheConfig(
        name="Principal Engineer Career Accelerator",
        category=NicheCategory.CAREER,
        description="Strategic career guidance for senior engineers targeting Principal/Distinguished roles",
        target_audience="Senior and Staff engineers aiming for Principal roles ($400K-600K+ comp)",
        value_proposition="Real Principal Engineer interview questions and promotion strategies from FAANG",
        content_sources=[
            ContentSource(
                "StaffEng", "https://staffeng.com/rss.xml", "rss", priority=1
            ),
            ContentSource(
                "High Growth Engineer",
                "https://careercutler.substack.com/feed",
                "rss",
                priority=1,
            ),
            ContentSource(
                "The Pragmatic Engineer",
                "https://blog.pragmaticengineer.com/rss/",
                "rss",
                priority=1,
            ),
            ContentSource("LeadDev", "https://leaddev.com/rss.xml", "rss", priority=2),
        ],
        content_ratio={"original": 0.75, "curated": 0.20, "syndicated": 0.05},
        keywords=[
            "principal engineer",
            "staff engineer",
            "technical leadership",
            "system design",
            "architecture review",
            "promotion",
            "compensation",
            "FAANG levels",
        ],
        exclude_keywords=["junior", "entry-level", "bootcamp"],
        summarization_prompt="""Summarize this content for Senior/Staff engineers targeting Principal roles at top tech companies.
        Focus on: 1) Scope and impact expectations at Principal level, 2) Specific skills gaps to address,
        3) Promotion packet strategies, 4) Compensation negotiation data points.
        Reference actual level guides from Google (L7+), Meta (E7+), Amazon (Principal+).""",
        curation_criteria="Content must address L6+ engineering challenges or Principal-level scope",
        tone_style="Strategic, insider perspective with specific examples from top tech companies",
        frequency="bi-weekly",
        optimal_send_time="Sunday 6PM EST",
        target_read_time=12,
        pricing_tiers={"free": 0, "pro": 30, "premium": 75},
        sponsorship_cpm=150,
        expected_conversion_rate=0.18,
        target_open_rate=0.52,
        target_click_rate=0.25,
        target_share_rate=0.15,
        template_name="executive_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "defense_tech_innovation": NicheConfig(
        name="Defense Tech Innovation Digest",
        category=NicheCategory.BUSINESS,
        description="DoD procurement opportunities and defense tech innovation for contractors and startups",
        target_audience="Defense contractors, Pentagon tech leaders, veteran-owned tech companies, defense VCs",
        value_proposition="How Anduril and Palantir win billion-dollar defense contracts",
        content_sources=[
            ContentSource(
                "Defense One", "https://www.defenseone.com/rss/", "rss", priority=1
            ),
            ContentSource(
                "C4ISRNET",
                "https://www.c4isrnet.com/arc/outboundfeeds/rss/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "Breaking Defense",
                "https://breakingdefense.com/feed/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "War on the Rocks", "https://warontherocks.com/feed/", "rss", priority=2
            ),
        ],
        content_ratio={"original": 0.70, "curated": 0.25, "syndicated": 0.05},
        keywords=[
            "SBIR",
            "STTR",
            "defense procurement",
            "dual-use",
            "DoD",
            "DARPA",
            "DIU",
            "AFWERX",
            "Pentagon",
            "defense tech",
        ],
        exclude_keywords=["politics", "partisan"],
        summarization_prompt="""Summarize defense tech content for defense contractors and veteran entrepreneurs.
        Focus on: 1) Procurement opportunities and contract vehicles (SBIR/STTR/OTA), 2) Technology requirements and gaps,
        3) Success stories from companies like Anduril, Palantir, Shield AI, 4) Timeline and funding amounts.
        Emphasize dual-use potential and commercial applications. Include veteran-owned business advantages.""",
        curation_criteria="Must relate to defense technology procurement, innovation, or veteran business opportunities",
        tone_style="Professional, opportunity-focused, with emphasis on mission impact and business potential",
        frequency="weekly",
        optimal_send_time="Thursday 7AM EST",
        target_read_time=10,
        pricing_tiers={"free": 0, "pro": 35, "enterprise": 350},
        sponsorship_cpm=180,
        expected_conversion_rate=0.22,
        target_open_rate=0.46,
        target_click_rate=0.20,
        target_share_rate=0.08,
        template_name="executive_newsletter.html",
        enable_code_snippets=False,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "veteran_executive_network": NicheConfig(
        name="Veteran Executive Network",
        category=NicheCategory.BUSINESS,
        description="Strategic insights for veteran CEOs, board members, and tech leaders",
        target_audience="Veteran CEOs, CTOs, board members, and C-suite executives transitioning from military",
        value_proposition="How veterans built Palantir, Anduril, and other billion-dollar companies",
        content_sources=[
            ContentSource(
                "Task & Purpose", "https://taskandpurpose.com/feed/", "rss", priority=2
            ),
            ContentSource(
                "Military.com",
                "https://www.military.com/rss-feeds/content",
                "rss",
                priority=2,
            ),
            ContentSource(
                "Techstars Military",
                "https://www.techstars.com/newsroom/feed",
                "rss",
                priority=1,
            ),
        ],
        content_ratio={"original": 0.75, "curated": 0.20, "syndicated": 0.05},
        keywords=[
            "veteran entrepreneur",
            "military transition",
            "veteran CEO",
            "leadership",
            "veteran-owned",
            "VOSB",
            "SDVOSB",
        ],
        exclude_keywords=["political", "partisan", "controversy"],
        summarization_prompt="""Summarize content for veteran executives and entrepreneurs.
        Focus on: 1) Military leadership principles applied to business, 2) Veteran success stories in tech and business,
        3) Transition strategies for senior military to C-suite, 4) Veteran business advantages (certifications, contracts).
        Emphasize transferable skills: strategic planning, crisis management, team building, operational excellence.""",
        curation_criteria="Must be relevant to veteran executives or demonstrate military-to-business leadership transition",
        tone_style="Professional, mission-focused, emphasizing service and leadership continuity",
        frequency="bi-weekly",
        optimal_send_time="Monday 6AM EST",
        target_read_time=10,
        pricing_tiers={"free": 0, "pro": 50, "enterprise": 400},
        sponsorship_cpm=200,
        expected_conversion_rate=0.28,
        target_open_rate=0.50,
        target_click_rate=0.24,
        target_share_rate=0.14,
        template_name="executive_newsletter.html",
        enable_code_snippets=False,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "latam_tech_talent": NicheConfig(
        name="LatAm Tech Talent Pipeline",
        category=NicheCategory.BUSINESS,
        description="Strategic guide for US companies hiring elite Latin American developers",
        target_audience="CTOs, VP Engineering, and HR leaders at US tech companies",
        value_proposition="Save 60% on engineering costs with top 1% LatAm talent",
        content_sources=[
            ContentSource(
                "Nearshore Americas",
                "https://nearshoreamericas.com/feed/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "LatamList", "https://latamlist.com/feed/", "rss", priority=1
            ),
            ContentSource("Contxto", "https://contxto.com/en/feed/", "rss", priority=2),
        ],
        content_ratio={"original": 0.70, "curated": 0.25, "syndicated": 0.05},
        keywords=[
            "nearshore",
            "remote developers",
            "Latin America",
            "talent pipeline",
            "staff augmentation",
            "timezone aligned",
        ],
        exclude_keywords=["outsourcing", "cheap labor"],
        summarization_prompt="""Summarize LatAm tech talent content for US executives hiring remote teams.
        Focus on: 1) Cost savings (typically 40-60% vs US), 2) Timezone advantages (1-3 hour difference),
        3) Cultural alignment and English proficiency, 4) Legal/tax considerations.
        Include specific salary benchmarks and successful case studies from US companies.""",
        curation_criteria="Must focus on senior/architect level talent, not junior outsourcing",
        tone_style="Executive-focused, emphasizing quality and strategic advantages",
        frequency="bi-weekly",
        optimal_send_time="Tuesday 10AM EST",
        target_read_time=8,
        pricing_tiers={"free": 0, "pro": 45, "enterprise": 450},
        sponsorship_cpm=175,
        expected_conversion_rate=0.20,
        target_open_rate=0.44,
        target_click_rate=0.18,
        target_share_rate=0.09,
        template_name="executive_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "faith_enterprise_tech": NicheConfig(
        name="Faith-Based Enterprise Tech",
        category=NicheCategory.BUSINESS,
        description="Digital transformation for faith-based organizations and religious enterprises",
        target_audience="CTOs/CIOs at faith-based organizations, megachurches, religious universities",
        value_proposition="How Life.Church and Hillsong scale to millions with technology",
        content_sources=[
            ContentSource(
                "Church IT Network",
                "https://churchitnetwork.com/feed/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "MinistryTech", "https://ministrytech.com/feed/", "rss", priority=1
            ),
            ContentSource(
                "FaithTech", "https://faithtech.com/feed/", "rss", priority=2
            ),
        ],
        content_ratio={"original": 0.75, "curated": 0.20, "syndicated": 0.05},
        keywords=[
            "church tech",
            "online giving",
            "livestreaming",
            "community platform",
            "faith technology",
            "religious education tech",
        ],
        exclude_keywords=["political", "controversial"],
        summarization_prompt="""Summarize faith-tech content for religious organization leaders.
        Focus on: 1) Digital engagement strategies that respect tradition, 2) Online giving optimization (typically 30-50% increase),
        3) Community building platforms, 4) Hybrid worship solutions.
        Be respectful of all faiths and emphasize inclusive technology.""",
        curation_criteria="Must be relevant to faith-based organizations with 500+ members",
        tone_style="Respectful, mission-focused, emphasizing community impact over technology",
        frequency="bi-weekly",
        optimal_send_time="Wednesday 9AM EST",
        target_read_time=8,
        pricing_tiers={"free": 0, "pro": 25, "enterprise": 250},
        sponsorship_cpm=120,
        expected_conversion_rate=0.15,
        target_open_rate=0.42,
        target_click_rate=0.16,
        target_share_rate=0.12,
        template_name="technical_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=True,
        enable_metrics=False,
    ),
    "family_office_tech": NicheConfig(
        name="Family Office Tech Insights",
        category=NicheCategory.BUSINESS,
        description="Technology investment insights for family offices and HNW individuals",
        target_audience="Family offices, HNW individuals, private wealth managers investing in tech",
        value_proposition="Where Bezos, Gates, and Thiel are investing their personal wealth",
        content_sources=[
            ContentSource(
                "PitchBook", "https://pitchbook.com/news/feed", "rss", priority=1
            ),
            ContentSource(
                "CB Insights", "https://www.cbinsights.com/feed", "rss", priority=1
            ),
            ContentSource(
                "StrictlyVC", "https://www.strictlyvc.com/feed/", "rss", priority=2
            ),
        ],
        content_ratio={"original": 0.80, "curated": 0.15, "syndicated": 0.05},
        keywords=[
            "family office",
            "direct investment",
            "venture capital",
            "private equity",
            "tech investment",
            "unicorn",
            "deep tech",
        ],
        exclude_keywords=["crypto", "NFT", "meme stocks"],
        summarization_prompt="""Summarize tech investment content for family offices and HNW individuals.
        Focus on: 1) Direct investment opportunities in tech, 2) Due diligence frameworks,
        3) Portfolio allocation strategies (typically 10-20% in tech), 4) Co-investment opportunities.
        Include valuation multiples and exit strategies. Reference investments by notable family offices.""",
        curation_criteria="Must involve investments of $1M+ or companies with $10M+ valuations",
        tone_style="Sophisticated, data-driven, with emphasis on risk-adjusted returns",
        frequency="weekly",
        optimal_send_time="Monday 7AM EST",
        target_read_time=12,
        pricing_tiers={"free": 0, "pro": 150, "premium": 1500},
        sponsorship_cpm=300,
        expected_conversion_rate=0.35,
        target_open_rate=0.55,
        target_click_rate=0.28,
        target_share_rate=0.18,
        template_name="executive_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=True,
        enable_metrics=True,
    ),
    "no_code_agency_empire": NicheConfig(
        name="No-Code Agency Empire",
        category=NicheCategory.BUSINESS,
        description="Scale from freelancer to $1M+ agency with no-code tools",
        target_audience="Agency owners, freelancers, and consultants building with Webflow/Bubble/Framer",
        value_proposition="From freelancer to $2M agency in 18 months using no-code",
        content_sources=[
            ContentSource(
                "Webflow Blog", "https://webflow.com/blog/feed", "rss", priority=1
            ),
            ContentSource(
                "No Code Founders",
                "https://nocodefounders.com/feed/",
                "rss",
                priority=1,
            ),
            ContentSource(
                "Makerpad", "https://www.makerpad.co/feed", "rss", priority=2
            ),
        ],
        content_ratio={"original": 0.70, "curated": 0.25, "syndicated": 0.05},
        keywords=[
            "no-code",
            "Webflow",
            "Bubble",
            "Framer",
            "agency",
            "MRR",
            "client acquisition",
            "recurring revenue",
        ],
        exclude_keywords=["employee", "job"],
        summarization_prompt="""Summarize no-code agency content for agency owners and freelancers.
        Focus on: 1) Client acquisition strategies (typical CAC $500-2000), 2) Pricing models and margins (50-70% typical),
        3) Scaling from freelancer to team, 4) Recurring revenue models.
        Include specific tools, pricing strategies, and growth metrics.""",
        curation_criteria="Must focus on agencies/freelancers earning $10K+ monthly",
        tone_style="Entrepreneurial, growth-focused, with specific tactics and numbers",
        frequency="weekly",
        optimal_send_time="Tuesday 9AM EST",
        target_read_time=8,
        pricing_tiers={"free": 0, "pro": 35, "accelerator": 297},
        sponsorship_cpm=140,
        expected_conversion_rate=0.18,
        target_open_rate=0.43,
        target_click_rate=0.19,
        target_share_rate=0.11,
        template_name="technical_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=False,
        enable_metrics=True,
    ),
    "tech_succession_planning": NicheConfig(
        name="Tech Succession Planning",
        category=NicheCategory.BUSINESS,
        description="Preparing family businesses for digital transformation and succession",
        target_audience="Family business owners, 2nd generation leaders, private equity partners",
        value_proposition="Modernize your family business for the next generation",
        content_sources=[
            ContentSource(
                "Family Business Magazine",
                "https://www.familybusinessmagazine.com/rss.xml",
                "rss",
                priority=1,
            ),
            ContentSource(
                "Harvard Business Review",
                "https://hbr.org/feeds/topics/succession-planning",
                "rss",
                priority=1,
            ),
        ],
        content_ratio={"original": 0.75, "curated": 0.20, "syndicated": 0.05},
        keywords=[
            "succession planning",
            "family business",
            "digital transformation",
            "next generation",
            "legacy modernization",
        ],
        exclude_keywords=["estate", "tax"],
        summarization_prompt="""Summarize succession and modernization content for family business leaders.
        Focus on: 1) Digital transformation strategies that preserve family values, 2) Succession planning for tech-forward businesses,
        3) Bridging generational gaps in technology adoption, 4) Case studies of successful transitions.
        Emphasize continuity and modernization balance.""",
        curation_criteria="Must be relevant to businesses with $10M+ revenue considering succession",
        tone_style="Respectful of tradition while embracing innovation, strategic and long-term focused",
        frequency="monthly",
        optimal_send_time="First Tuesday 8AM EST",
        target_read_time=10,
        pricing_tiers={"free": 0, "pro": 40, "advisory": 400},
        sponsorship_cpm=160,
        expected_conversion_rate=0.20,
        target_open_rate=0.45,
        target_click_rate=0.18,
        target_share_rate=0.10,
        template_name="technical_newsletter.html",
        enable_code_snippets=True,
        enable_diagrams=True,
        enable_metrics=False,
    ),
}


def get_niche_config(niche_name: str) -> NicheConfig:
    """Get configuration for a specific niche."""
    if niche_name not in NEWSLETTER_NICHES:
        raise ValueError(f"Unknown niche: {niche_name}")
    return NEWSLETTER_NICHES[niche_name]


def get_niches_by_category(category: NicheCategory) -> List[NicheConfig]:
    """Get all niches in a specific category."""
    return [
        config for config in NEWSLETTER_NICHES.values() if config.category == category
    ]


def get_all_niches() -> List[str]:
    """Get list of all available niche names."""
    return list(NEWSLETTER_NICHES.keys())


def calculate_potential_revenue(
    niche_name: str, subscriber_count: int, paid_conversion_rate: float = None
) -> Dict[str, float]:
    """Calculate potential revenue for a niche."""
    config = get_niche_config(niche_name)

    if paid_conversion_rate is None:
        paid_conversion_rate = config.expected_conversion_rate

    # Calculate subscription revenue
    paid_subscribers = int(subscriber_count * paid_conversion_rate)
    monthly_subscription_revenue = paid_subscribers * config.pricing_tiers.get("pro", 0)

    # Calculate sponsorship revenue (assuming 4 newsletters per month)
    monthly_sponsorship_revenue = (subscriber_count / 1000) * config.sponsorship_cpm * 4

    return {
        "monthly_subscription": monthly_subscription_revenue,
        "monthly_sponsorship": monthly_sponsorship_revenue,
        "monthly_total": monthly_subscription_revenue + monthly_sponsorship_revenue,
        "annual_total": (monthly_subscription_revenue + monthly_sponsorship_revenue)
        * 12,
        "paid_subscribers": paid_subscribers,
        "conversion_rate": paid_conversion_rate,
    }

# Export for compatibility
niche_configs = NEWSLETTER_NICHES
