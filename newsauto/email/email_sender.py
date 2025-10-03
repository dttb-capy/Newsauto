"""Email sending functionality."""

import asyncio
import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict, List, Optional

import aiosmtplib
from jinja2 import Template

logger = logging.getLogger(__name__)


@dataclass
class SMTPConfig:
    """SMTP server configuration."""

    host: str = "localhost"
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    from_email: str = "newsletter@example.com"
    from_name: str = "Newsletter"
    timeout: int = 30


class EmailSender:
    """Email sending service."""

    def __init__(self, config: SMTPConfig):
        """Initialize email sender.

        Args:
            config: SMTP configuration
        """
        self.config = config
        self._client: Optional[aiosmtplib.SMTP] = None

    async def connect(self):
        """Connect to SMTP server."""
        if self._client is None:
            self._client = aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                timeout=self.config.timeout,
            )

        if not self._client.is_connected:
            await self._client.connect()

            if self.config.use_tls:
                await self._client.starttls()

            if self.config.username and self.config.password:
                await self._client.login(self.config.username, self.config.password)

    async def disconnect(self):
        """Disconnect from SMTP server."""
        if self._client and self._client.is_connected:
            await self._client.quit()
        self._client = None

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Send email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Optional plain text content
            reply_to: Optional reply-to address
            headers: Optional additional headers

        Returns:
            Success status
        """
        try:
            await self.connect()

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr((self.config.from_name, self.config.from_email))
            msg["To"] = to_email

            if reply_to:
                msg["Reply-To"] = reply_to

            # Add custom headers
            if headers:
                for key, value in headers.items():
                    msg[key] = value

            # Add text part
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # Send email
            await self._client.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_bulk(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        html_template: str,
        text_template: Optional[str] = None,
        batch_size: int = 50,
        delay_between_batches: float = 1.0,
    ) -> Dict[str, Any]:
        """Send bulk emails.

        Args:
            recipients: List of recipient dictionaries with email and context
            subject: Email subject
            html_template: HTML template string
            text_template: Optional text template string
            batch_size: Number of emails per batch
            delay_between_batches: Delay between batches in seconds

        Returns:
            Sending results
        """
        results = {"sent": [], "failed": [], "total": len(recipients)}

        # Process in batches
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            # Send emails in parallel within batch
            tasks = []
            for recipient in batch:
                email = recipient["email"]
                context = recipient.get("context", {})

                # Render templates
                html_content = Template(html_template).render(**context)
                text_content = None
                if text_template:
                    text_content = Template(text_template).render(**context)

                # Create send task
                task = self.send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                )
                tasks.append((email, task))

            # Execute batch
            for email, task in tasks:
                success = await task
                if success:
                    results["sent"].append(email)
                else:
                    results["failed"].append(email)

            # Delay between batches
            if i + batch_size < len(recipients):
                await asyncio.sleep(delay_between_batches)

        return results


class EmailValidator:
    """Email validation utilities."""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if email address is valid.

        Args:
            email: Email address to validate

        Returns:
            Validation status
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def clean_email(email: str) -> str:
        """Clean and normalize email address.

        Args:
            email: Email address to clean

        Returns:
            Cleaned email address
        """
        return email.strip().lower()

    async def send_email_with_retry(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> bool:
        """Send email with retry logic.

        Args:
            to_email: Recipient email
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content
            headers: Additional headers
            max_retries: Maximum number of retries

        Returns:
            Success status
        """
        import asyncio

        for attempt in range(max_retries):
            try:
                result = await self.send_email(
                    to_email=to_email,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    headers=headers,
                )
                if result:
                    return True
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                else:
                    raise
        return False


class EmailBuilder:
    """Email content builder."""

    @staticmethod
    def add_tracking_pixel(
        html_content: str, tracking_id: str, tracking_url: str
    ) -> str:
        """Add tracking pixel to HTML content.

        Args:
            html_content: HTML content
            tracking_id: Tracking identifier
            tracking_url: Base tracking URL

        Returns:
            HTML with tracking pixel
        """
        pixel = f'<img src="{tracking_url}/open/{tracking_id}" width="1" height="1" />'

        # Add before closing body tag
        if "</body>" in html_content:
            return html_content.replace("</body>", f"{pixel}</body>")
        else:
            return html_content + pixel

    @staticmethod
    def add_click_tracking(
        html_content: str, tracking_id: str, tracking_url: str
    ) -> str:
        """Add click tracking to links.

        Args:
            html_content: HTML content
            tracking_id: Tracking identifier
            tracking_url: Base tracking URL

        Returns:
            HTML with tracked links
        """
        from urllib.parse import quote

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Track all links
        for link in soup.find_all("a", href=True):
            original_url = link["href"]

            # Skip mailto and internal anchors
            if original_url.startswith(("mailto:", "#")):
                continue

            # Create tracking URL
            tracked_url = (
                f"{tracking_url}/click/{tracking_id}?url={quote(original_url)}"
            )
            link["href"] = tracked_url

        return str(soup)

    @staticmethod
    def personalize_content(template: str, subscriber_data: Dict[str, Any]) -> str:
        """Personalize content for subscriber.

        Args:
            template: Template string with placeholders
            subscriber_data: Subscriber data dictionary

        Returns:
            Personalized content
        """
        from jinja2 import Template

        tmpl = Template(template)
        return tmpl.render(**subscriber_data)
