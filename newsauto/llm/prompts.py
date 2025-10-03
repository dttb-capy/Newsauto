"""Prompt templates for different newsletter types and content."""


class PromptTemplates:
    """Collection of prompt templates for various LLM operations."""

    # Newsletter-specific summarization prompts
    NEWSLETTER_PROMPTS = {
        "tech": """You are a tech newsletter editor writing for busy professionals.
Summarize this article focusing on:
- Practical implications and real-world applications
- Key technical innovations or breakthroughs
- What this means for developers/engineers
Keep it concise (2-3 sentences) and engaging.

Article: {text}
Summary:""",
        "business": """You are a business newsletter editor for executives and entrepreneurs.
Summarize this article focusing on:
- Business impact and opportunities
- Strategic implications
- Key metrics or financial data
Write in a professional yet accessible tone (2-3 sentences).

Article: {text}
Summary:""",
        "research": """You are summarizing research for a technical audience.
Focus on:
- Main findings and methodology
- Statistical significance and limitations
- Real-world applications
Be precise and accurate (3-4 sentences).

Paper: {text}
Summary:""",
        "news": """You are a news editor creating a newsletter digest.
Summarize this article with:
- Key facts and developments
- Why this matters now
- What to expect next
Keep it factual and engaging (2-3 sentences).

Article: {text}
Summary:""",
        "ai": """You are an AI/ML newsletter editor for practitioners and researchers.
Summarize focusing on:
- Technical approach and innovations
- Performance metrics and benchmarks
- Practical applications and limitations
Be technically accurate but accessible (2-4 sentences).

Article: {text}
Summary:""",
        "startup": """You are writing for startup founders and investors.
Highlight:
- Business model and market opportunity
- Funding and growth metrics
- Key differentiators
Keep it concise and action-oriented (2-3 sentences).

Article: {text}
Summary:""",
        "security": """You are a cybersecurity newsletter editor.
Focus on:
- Threat details and impact
- Affected systems/vendors
- Mitigation steps
Be clear and actionable (2-3 sentences).

Article: {text}
Summary:""",
    }

    # Key points extraction prompts
    KEY_POINTS_PROMPTS = {
        "default": """Extract the {max_points} most important points from this article.
Format as a numbered list. Each point should be one clear, concise sentence.

Article: {text}

Key Points:""",
        "actionable": """Extract {max_points} actionable insights from this content.
Focus on what readers can actually do or implement.
Format as a numbered list.

Content: {text}

Actionable Insights:""",
        "technical": """Extract {max_points} key technical details from this article.
Focus on specifications, features, and implementation details.
Format as a numbered list.

Article: {text}

Technical Points:""",
    }

    # Title generation prompts
    TITLE_PROMPTS = {
        "engaging": """Create an engaging, informative title for this article.
The title should be 5-10 words and capture the main point.
Make it interesting but not clickbait.

Article: {text}

Title:""",
        "professional": """Create a professional, straightforward title.
Be clear and descriptive (5-10 words).

Article: {text}

Title:""",
        "seo": """Create an SEO-optimized title for this article.
Include likely search keywords while remaining natural.
Keep it under 60 characters.

Article: {text}

Title:""",
    }

    # Trend analysis prompts
    TREND_PROMPTS = {
        "weekly": """Analyze these article summaries from the past week.
Identify:
1. Top 3-5 emerging trends or themes
2. Any contradictions or debates
3. Key takeaways for readers
4. What to watch for next week

Summaries: {summaries}

Analysis:""",
        "comparison": """Compare and contrast these articles.
Identify:
1. Common themes and agreements
2. Points of disagreement or debate
3. Unique insights from each source
4. Overall consensus (if any)

Articles: {summaries}

Comparison:""",
    }

    # Content classification prompts
    CLASSIFICATION_PROMPTS = {
        "category": """Classify this text into ONE category: {categories}

Text: {text}

Category (respond with just the category name):""",
        "tags": """Generate 3-5 relevant tags for this article.
Tags should be single words or short phrases.

Article: {text}

Tags (comma-separated):""",
        "audience": """Identify the primary audience for this content.
Choose from: beginners, intermediate, advanced, expert

Content: {text}

Audience level:""",
    }

    # Email subject line prompts
    SUBJECT_PROMPTS = {
        "newsletter": """Create an email subject line for a newsletter containing these topics:
{topics}

Requirements:
- Under 50 characters
- Create urgency or curiosity
- Mention the most interesting topic
- Include emoji if appropriate for the audience

Subject:""",
        "personal": """Create a personalized email subject line.
Newsletter: {newsletter_name}
Top story: {top_story}
Subscriber name: {subscriber_name}

Make it personal and engaging (under 50 characters).

Subject:""",
    }

    # Sentiment analysis prompts
    SENTIMENT_PROMPTS = {
        "basic": """Analyze the sentiment of this text.
Respond with: positive, negative, or neutral
Also provide confidence (0-100).

Text: {text}

Sentiment:
Confidence:""",
        "detailed": """Provide detailed sentiment analysis:
1. Overall sentiment (positive/negative/neutral)
2. Emotional tone (professional/casual/urgent/etc.)
3. Key emotional triggers in the text
4. Confidence score (0-100)

Text: {text}

Analysis:""",
    }

    @classmethod
    def get_prompt(cls, category: str, template_type: str, **kwargs) -> str:
        """Get a formatted prompt template.

        Args:
            category: Prompt category (newsletter, key_points, etc.)
            template_type: Specific template within category
            **kwargs: Variables to format into template

        Returns:
            Formatted prompt string
        """
        templates = {
            "newsletter": cls.NEWSLETTER_PROMPTS,
            "key_points": cls.KEY_POINTS_PROMPTS,
            "title": cls.TITLE_PROMPTS,
            "trend": cls.TREND_PROMPTS,
            "classification": cls.CLASSIFICATION_PROMPTS,
            "subject": cls.SUBJECT_PROMPTS,
            "sentiment": cls.SENTIMENT_PROMPTS,
        }

        category_templates = templates.get(category, {})
        template = category_templates.get(template_type, "")

        if not template:
            # Fallback to default template
            template = category_templates.get("default", "")

        return template.format(**kwargs)

    @classmethod
    def get_system_prompt(cls, role: str) -> str:
        """Get system prompt for specific role.

        Args:
            role: Role identifier

        Returns:
            System prompt string
        """
        system_prompts = {
            "newsletter_editor": (
                "You are a professional newsletter editor with expertise in "
                "creating concise, engaging summaries for busy readers. "
                "Focus on clarity, relevance, and actionable insights."
            ),
            "tech_analyst": (
                "You are a technical analyst specializing in software, "
                "AI, and emerging technologies. Provide accurate, detailed "
                "analysis while remaining accessible."
            ),
            "business_analyst": (
                "You are a business analyst focused on market trends, "
                "strategy, and financial implications. Be data-driven "
                "and strategic in your analysis."
            ),
            "content_curator": (
                "You are a content curator skilled at identifying "
                "the most important and interesting information "
                "from various sources."
            ),
        }

        return system_prompts.get(role, system_prompts["newsletter_editor"])

    @classmethod
    def create_custom_prompt(
        cls,
        instruction: str,
        context: str = None,
        constraints: list = None,
        examples: list = None,
    ) -> str:
        """Create a custom prompt with structure.

        Args:
            instruction: Main instruction
            context: Additional context
            constraints: List of constraints
            examples: List of examples

        Returns:
            Formatted custom prompt
        """
        prompt_parts = [instruction]

        if context:
            prompt_parts.append(f"\nContext: {context}")

        if constraints:
            prompt_parts.append("\nConstraints:")
            for constraint in constraints:
                prompt_parts.append(f"- {constraint}")

        if examples:
            prompt_parts.append("\nExamples:")
            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"{i}. {example}")

        return "\n".join(prompt_parts)
