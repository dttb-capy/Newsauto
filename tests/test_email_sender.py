"""Test suite for email sending."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from newsauto.email.delivery_manager import DeliveryManager
from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.email.tracking import EmailTracker


@pytest.fixture
def smtp_config():
    """Create SMTP configuration."""
    return SMTPConfig(
        host="smtp.test.com",
        port=587,
        username="test@example.com",
        password="testpass",
        use_tls=True,
        from_email="newsletter@test.com",
        from_name="Test Newsletter",
        timeout=30,
    )


@pytest.fixture
def email_sender(smtp_config):
    """Create EmailSender instance."""
    return EmailSender(smtp_config)


@pytest.fixture
def mock_smtp_client():
    """Create mock SMTP client."""
    mock = AsyncMock()
    mock.is_connected = False
    mock.connect = AsyncMock()
    mock.starttls = AsyncMock()
    mock.login = AsyncMock()
    mock.send_message = AsyncMock()
    mock.quit = AsyncMock()
    return mock


class TestEmailSender:
    """Test email sending functionality."""

    @pytest.mark.asyncio
    async def test_connect(self, email_sender, mock_smtp_client):
        """Test SMTP connection."""
        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            await email_sender.connect()

            # Verify connection sequence
            mock_smtp_client.connect.assert_called_once()
            mock_smtp_client.starttls.assert_called_once()
            mock_smtp_client.login.assert_called_once_with(
                "test@example.com", "testpass"
            )

    @pytest.mark.asyncio
    async def test_connect_no_auth(self, mock_smtp_client):
        """Test connection without authentication."""
        config = SMTPConfig(host="localhost", port=1025, use_tls=False)
        sender = EmailSender(config)

        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            await sender.connect()

            # Verify no login was attempted
            mock_smtp_client.connect.assert_called_once()
            mock_smtp_client.starttls.assert_not_called()
            mock_smtp_client.login.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect(self, email_sender, mock_smtp_client):
        """Test SMTP disconnection."""
        mock_smtp_client.is_connected = True

        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            email_sender._client = mock_smtp_client
            await email_sender.disconnect()

            # Verify disconnection
            mock_smtp_client.quit.assert_called_once()
            assert email_sender._client is None

    @pytest.mark.asyncio
    async def test_send_email(self, email_sender, mock_smtp_client):
        """Test sending a single email."""
        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            result = await email_sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<html><body>Test HTML</body></html>",
                text_content="Test Text",
            )

            # Verify success
            assert result is True
            mock_smtp_client.send_message.assert_called_once()

            # Verify message structure
            sent_message = mock_smtp_client.send_message.call_args[0][0]
            assert sent_message["Subject"] == "Test Subject"
            assert sent_message["To"] == "recipient@example.com"

    @pytest.mark.asyncio
    async def test_send_email_with_headers(self, email_sender, mock_smtp_client):
        """Test sending email with custom headers."""
        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            await email_sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<html><body>Test</body></html>",
                headers={"X-Campaign-ID": "test-123", "X-Newsletter-ID": "1"},
            )

            # Verify headers were added
            sent_message = mock_smtp_client.send_message.call_args[0][0]
            assert sent_message["X-Campaign-ID"] == "test-123"
            assert sent_message["X-Newsletter-ID"] == "1"

    @pytest.mark.asyncio
    async def test_send_email_error(self, email_sender, mock_smtp_client):
        """Test email sending with error."""
        mock_smtp_client.send_message.side_effect = Exception("SMTP error")

        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            result = await email_sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                html_content="<html><body>Test</body></html>",
            )

            # Verify failure
            assert result is False

    @pytest.mark.asyncio
    async def test_send_batch(self, email_sender, mock_smtp_client):
        """Test batch email sending."""
        recipients = [
            {"email": "user1@example.com", "name": "User 1"},
            {"email": "user2@example.com", "name": "User 2"},
            {"email": "user3@example.com", "name": "User 3"},
        ]

        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            results = await email_sender.send_batch(
                recipients=recipients,
                subject="Batch Test",
                html_template="<html>Hello {{name}}</html>",
                text_template="Hello {{name}}",
            )

            # Verify all emails were sent
            assert len(results) == 3
            assert all(r["success"] for r in results)
            assert mock_smtp_client.send_message.call_count == 3

    @pytest.mark.asyncio
    async def test_send_batch_with_personalization(
        self, email_sender, mock_smtp_client
    ):
        """Test batch sending with personalization."""
        recipients = [
            {"email": "user1@example.com", "name": "Alice", "city": "NYC"},
            {"email": "user2@example.com", "name": "Bob", "city": "LA"},
        ]

        with patch("aiosmtplib.SMTP", return_value=mock_smtp_client):
            await email_sender.send_batch(
                recipients=recipients,
                subject="Hello {{name}}",
                html_template="<html>Hello {{name}} from {{city}}</html>",
                text_template="Hello {{name}} from {{city}}",
            )

            # Verify personalization
            calls = mock_smtp_client.send_message.call_args_list
            msg1 = calls[0][0][0]
            msg2 = calls[1][0][0]

            # Check subjects are personalized
            assert msg1["Subject"] == "Hello Alice"
            assert msg2["Subject"] == "Hello Bob"


class TestDeliveryManager:
    """Test email delivery manager."""

    @pytest.mark.asyncio
    async def test_delivery_rate_limiting(self, smtp_config, db_session):
        """Test rate limiting in delivery manager."""
        delivery_manager = DeliveryManager(db_session, smtp_config)

        recipients = [f"user{i}@example.com" for i in range(5)]

        with patch("aiosmtplib.SMTP") as mock_smtp:
            mock_client = AsyncMock()
            mock_smtp.return_value = mock_client

            start_time = asyncio.get_event_loop().time()
            # Create mock edition and subscribers
            edition = Mock()
            edition.id = 1
            edition.subject = "Test"
            edition.newsletter_id = 1
            edition.content = {"sections": []}
            edition.newsletter = Mock(name="Test Newsletter")

            subscribers = [
                Mock(id=i, email=email, name=f"User {i}")
                for i, email in enumerate(recipients)
            ]

            # Mock the generator methods
            delivery_manager.newsletter_generator.render_edition = Mock(
                return_value=("<html>Test</html>", "Test")
            )
            delivery_manager._create_tracking_id = Mock(return_value="tracking123")
            delivery_manager._add_tracking = Mock(
                return_value="<html>Test with tracking</html>"
            )

            await delivery_manager._send_batch(
                edition=edition,
                recipients=subscribers,
                test_mode=True,
            )
            elapsed = asyncio.get_event_loop().time() - start_time

            # With rate limit of 10/second, 5 emails should take ~0.5 seconds
            # Allow some margin for execution time
            assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_delivery_retry(self, smtp_config, db_session):
        """Test retry logic in delivery manager."""
        delivery_manager = DeliveryManager(db_session, smtp_config)

        with patch("aiosmtplib.SMTP") as mock_smtp:
            mock_client = AsyncMock()
            # Fail twice, then succeed
            mock_client.send_message.side_effect = [
                Exception("Temporary error"),
                Exception("Temporary error"),
                None,
            ]
            mock_smtp.return_value = mock_client

            # Create mock edition and subscribers
            edition = Mock()
            edition.id = 1
            edition.subject = "Test"
            edition.newsletter_id = 1
            edition.content = {"sections": []}
            edition.newsletter = Mock(name="Test Newsletter")

            subscriber = Mock(id=1, email="test@example.com", name="Test User")

            # Mock the generator methods
            delivery_manager.newsletter_generator.render_edition = Mock(
                return_value=("<html>Test</html>", "Test")
            )
            delivery_manager._create_tracking_id = Mock(return_value="tracking123")
            delivery_manager._add_tracking = Mock(
                return_value="<html>Test with tracking</html>"
            )

            results = await delivery_manager._send_batch(
                edition=edition,
                recipients=[subscriber],
                test_mode=True,
            )

            # Verify retry worked
            assert results[0]["success"] is True
            assert results[0]["retries"] == 2
            assert mock_client.send_message.call_count == 3


class TestEmailTracker:
    """Test email tracking functionality."""

    def test_add_tracking_pixel(self):
        """Test adding tracking pixel to HTML."""
        tracker = EmailTracker(base_url="https://track.example.com")

        html = "<html><body>Hello</body></html>"
        tracked_html = tracker.add_tracking_pixel(html, edition_id=1, subscriber_id=123)

        # Verify pixel was added
        assert "track.example.com/open" in tracked_html
        assert "edition_id=1" in tracked_html
        assert "subscriber_id=123" in tracked_html
        assert "<img " in tracked_html

    def test_track_links(self):
        """Test link tracking in HTML."""
        tracker = EmailTracker(base_url="https://track.example.com")

        html = """
        <html>
            <body>
                <a href="https://example.com/article1">Article 1</a>
                <a href="https://example.com/article2">Article 2</a>
            </body>
        </html>
        """

        tracked_html = tracker.track_links(html, edition_id=1, subscriber_id=123)

        # Verify links were tracked
        assert "track.example.com/click" in tracked_html
        assert "url=https%3A%2F%2Fexample.com%2Farticle1" in tracked_html
        assert "url=https%3A%2F%2Fexample.com%2Farticle2" in tracked_html
        assert tracked_html.count("track.example.com/click") == 2

    def test_generate_unsubscribe_link(self):
        """Test unsubscribe link generation."""
        tracker = EmailTracker(base_url="https://track.example.com")

        link = tracker.generate_unsubscribe_link(
            subscriber_id=123, newsletter_id=1, token="abc123"
        )

        # Verify link structure
        assert link.startswith("https://track.example.com/unsubscribe")
        assert "subscriber_id=123" in link
        assert "newsletter_id=1" in link
        assert "token=abc123" in link

    def test_track_full_email(self):
        """Test tracking all elements in email."""
        tracker = EmailTracker(base_url="https://track.example.com")

        html = """
        <html>
            <body>
                <h1>Newsletter</h1>
                <a href="https://example.com/article">Read Article</a>
                <p>Content here</p>
            </body>
        </html>
        """

        tracked = tracker.track_email(
            html, edition_id=1, subscriber_id=123, newsletter_id=5
        )

        # Verify all tracking elements
        assert "track.example.com/open" in tracked  # Pixel
        assert "track.example.com/click" in tracked  # Link tracking
        assert "track.example.com/unsubscribe" in tracked  # Unsubscribe
        assert "</body>" in tracked  # Pixel before closing body


class TestEmailValidation:
    """Test email validation."""

    def test_validate_email_format(self):
        """Test email format validation."""
        from newsauto.email.email_sender import EmailValidator

        validator = EmailValidator()

        # Valid emails
        assert validator.validate("test@example.com") is True
        assert validator.validate("user.name@example.co.uk") is True
        assert validator.validate("user+tag@example.com") is True

        # Invalid emails
        assert validator.validate("invalid") is False
        assert validator.validate("@example.com") is False
        assert validator.validate("user@") is False
        assert validator.validate("user @example.com") is False

    @pytest.mark.asyncio
    async def test_validate_mx_record(self):
        """Test MX record validation."""
        from newsauto.email.email_sender import EmailValidator

        validator = EmailValidator()

        # Test with known domain
        valid = await validator.validate_mx("gmail.com")
        assert valid is True

        # Test with invalid domain
        valid = await validator.validate_mx("invalid-domain-12345.com")
        assert valid is False
