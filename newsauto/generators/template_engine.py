"""Template engine for newsletter rendering."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import markdown
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Engine for rendering newsletter templates."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template engine.

        Args:
            template_dir: Directory containing templates
        """
        if template_dir is None:
            template_dir = str(Path(__file__).parent.parent / "templates")

        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self.env.filters["markdown"] = self.markdown_filter
        self.env.filters["dateformat"] = self.dateformat_filter
        self.env.filters["truncate_summary"] = self.truncate_summary

        # Cache compiled templates
        self._template_cache: Dict[str, Template] = {}

    def markdown_filter(self, text: str) -> str:
        """Convert markdown to HTML.

        Args:
            text: Markdown text

        Returns:
            HTML string
        """
        return markdown.markdown(
            text, extensions=["extra", "codehilite", "nl2br"], output_format="html5"
        )

    def dateformat_filter(self, date: datetime, format: str = "%B %d, %Y") -> str:
        """Format datetime object.

        Args:
            date: Datetime to format
            format: strftime format string

        Returns:
            Formatted date string
        """
        return date.strftime(format) if date else ""

    def truncate_summary(self, text: str, length: int = 200) -> str:
        """Truncate text to specified length.

        Args:
            text: Text to truncate
            length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= length:
            return text

        # Find the last complete word before the length limit
        truncated = text[:length].rsplit(" ", 1)[0]
        return f"{truncated}..."

    def render_newsletter(
        self, template_name: str, context: Dict[str, Any]
    ) -> tuple[str, str]:
        """Render newsletter template.

        Args:
            template_name: Name of template file
            context: Template context variables

        Returns:
            Tuple of (html_content, text_content)
        """
        # Add default context
        default_context = {
            "current_year": datetime.now().year,
            "generated_at": datetime.utcnow(),
            "app_name": "Newsauto",
        }

        full_context = {**default_context, **context}

        # Render HTML version
        html_template = self.get_template(f"{template_name}.html")
        html_content = html_template.render(full_context)

        # Render text version
        text_template_path = f"{template_name}.txt"
        try:
            text_template = self.get_template(text_template_path)
            text_content = text_template.render(full_context)
        except Exception:
            # Fallback to generating text from HTML
            text_content = self.html_to_text(html_content)

        return html_content, text_content

    def get_template(self, name: str) -> Template:
        """Get cached template or load from file.

        Args:
            name: Template name

        Returns:
            Jinja2 template
        """
        if name not in self._template_cache:
            self._template_cache[name] = self.env.get_template(name)
        return self._template_cache[name]

    def html_to_text(self, html: str) -> str:
        """Convert HTML to plain text.

        Args:
            html: HTML content

        Returns:
            Plain text content
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    def create_default_templates(self):
        """Create default newsletter templates."""
        templates_dir = Path(__file__).parent.parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        # Default HTML template
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .article {
            background: #f9f9f9;
            border-left: 3px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }
        .article-title { font-weight: bold; color: #2c3e50; }
        .article-meta { font-size: 0.9em; color: #7f8c8d; }
        .article-summary { margin-top: 10px; }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>{{ newsletter.name }}</h1>
    <p>{{ newsletter.description }}</p>

    {% for section in sections %}
    <h2>{{ section.title }}</h2>

    {% for article in section.articles %}
    <div class="article">
        <div class="article-title">
            <a href="{{ article.url }}">{{ article.title }}</a>
        </div>
        <div class="article-meta">
            {% if article.author %}By {{ article.author }} | {% endif %}
            {{ article.published_at|dateformat }}
        </div>
        <div class="article-summary">
            {{ article.summary|truncate_summary(250) }}
        </div>
    </div>
    {% endfor %}
    {% endfor %}

    <div class="footer">
        <p>© {{ current_year }} {{ app_name }}. All rights reserved.</p>
        <p>
            <a href="{{ unsubscribe_url }}">Unsubscribe</a> |
            <a href="{{ preferences_url }}">Update Preferences</a>
        </p>
    </div>
</body>
</html>"""

        # Default text template
        text_template = """{{ newsletter.name }}
{{ '=' * newsletter.name|length }}

{{ newsletter.description }}

{% for section in sections %}
{{ section.title }}
{{ '-' * section.title|length }}

{% for article in section.articles %}
* {{ article.title }}
  {% if article.author %}By {{ article.author }} | {% endif %}{{ article.published_at|dateformat }}
  {{ article.url }}

  {{ article.summary|truncate_summary(200) }}

{% endfor %}
{% endfor %}

---
© {{ current_year }} {{ app_name }}. All rights reserved.
Unsubscribe: {{ unsubscribe_url }}
Update Preferences: {{ preferences_url }}"""

        # Save default templates
        (templates_dir / "default.html").write_text(html_template)
        (templates_dir / "default.txt").write_text(text_template)

        logger.info("Created default templates")


class ResponsiveTemplateEngine(TemplateEngine):
    """Template engine with responsive email design."""

    def render_responsive_newsletter(self, context: Dict[str, Any]) -> tuple[str, str]:
        """Render responsive newsletter template.

        Args:
            context: Template context variables

        Returns:
            Tuple of (html_content, text_content)
        """
        # Use responsive template
        return self.render_newsletter("responsive", context)

    def create_responsive_template(self):
        """Create responsive email template."""
        templates_dir = Path(__file__).parent.parent / "templates"
        templates_dir.mkdir(exist_ok=True)

        responsive_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        /* Reset styles */
        body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
        table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
        img { -ms-interpolation-mode: bicubic; border: 0; outline: none; text-decoration: none; }

        /* Mobile styles */
        @media screen and (max-width: 600px) {
            .container { width: 100% !important; }
            .content { padding: 10px !important; }
            .article { padding: 10px !important; }
            h1 { font-size: 24px !important; }
            h2 { font-size: 20px !important; }
        }
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" width="100%">
        <tr>
            <td align="center" style="padding: 20px;">
                <table class="container" role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td class="content" style="padding: 30px;">
                            <!-- Newsletter content here -->
                            <h1 style="color: #333; margin: 0 0 20px 0;">{{ newsletter.name }}</h1>

                            {% for section in sections %}
                            <h2 style="color: #555; margin: 30px 0 15px 0;">{{ section.title }}</h2>

                            {% for article in section.articles %}
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 20px;">
                                <tr>
                                    <td class="article" style="padding: 15px; background-color: #f9f9f9; border-left: 3px solid #3498db;">
                                        <h3 style="margin: 0 0 10px 0;">
                                            <a href="{{ article.url }}" style="color: #2c3e50; text-decoration: none;">{{ article.title }}</a>
                                        </h3>
                                        <p style="margin: 5px 0; color: #777; font-size: 14px;">
                                            {% if article.author %}{{ article.author }} | {% endif %}{{ article.published_at|dateformat }}
                                        </p>
                                        <p style="margin: 10px 0 0 0; color: #333;">
                                            {{ article.summary|truncate_summary(200) }}
                                        </p>
                                    </td>
                                </tr>
                            </table>
                            {% endfor %}
                            {% endfor %}

                            <!-- Footer -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-top: 40px; border-top: 1px solid #ddd;">
                                <tr>
                                    <td align="center" style="padding: 20px 0; color: #777; font-size: 12px;">
                                        © {{ current_year }} {{ app_name }}. All rights reserved.<br>
                                        <a href="{{ unsubscribe_url }}" style="color: #3498db;">Unsubscribe</a> |
                                        <a href="{{ preferences_url }}" style="color: #3498db;">Preferences</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        (templates_dir / "responsive.html").write_text(responsive_html)
        logger.info("Created responsive template")
