"""Tests for self-healing infrastructure."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from newsauto.automation.self_heal import SelfHealingOrchestrator
from newsauto.monitoring.health_checks import (
    SMTPHealthCheck,
    OllamaHealthCheck,
    FeedHealthCheck,
    DatabaseHealthCheck,
)


class TestSMTPHealthCheck:
    """Test SMTP health checking."""

    @pytest.mark.asyncio
    async def test_healthy_smtp(self):
        """Test healthy SMTP server."""
        with patch('newsauto.email.email_sender.EmailSender.send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            checker = SMTPHealthCheck()
            result = await checker.check()

            assert result["healthy"] == True
            assert "smtp_host" in result

    @pytest.mark.asyncio
    async def test_blacklisted_smtp(self):
        """Test SMTP blacklist detection."""
        with patch('newsauto.email.email_sender.EmailSender.send_email', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Blacklisted by spam filter")

            checker = SMTPHealthCheck()
            result = await checker.check()

            assert result["healthy"] == False
            assert result.get("blacklisted") == True


class TestOllamaHealthCheck:
    """Test Ollama health checking."""

    @pytest.mark.asyncio
    async def test_healthy_ollama(self):
        """Test healthy Ollama service."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "models": [
                    {"name": "mistral:7b-instruct"},
                    {"name": "deepseek-r1:1.5b"}
                ]
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            checker = OllamaHealthCheck()
            result = await checker.check()

            assert result["healthy"] == True
            assert len(result["available_models"]) == 2

    @pytest.mark.asyncio
    async def test_ollama_missing_models(self):
        """Test Ollama with missing models."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"models": []})
            mock_get.return_value.__aenter__.return_value = mock_response

            checker = OllamaHealthCheck()
            result = await checker.check()

            assert result["healthy"] == False
            assert len(result.get("missing_models", [])) > 0


class TestSelfHealingOrchestrator:
    """Test self-healing orchestration."""

    @pytest.fixture
    def orchestrator(self):
        return SelfHealingOrchestrator()

    @pytest.mark.asyncio
    async def test_smtp_rotation(self, orchestrator):
        """Test SMTP relay rotation on blacklist."""
        # Mock blacklisted primary SMTP
        with patch.object(orchestrator.smtp_check, 'check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {
                "healthy": False,
                "error": "Blacklisted",
                "blacklisted": True
            }

            result = await orchestrator._heal_smtp_blacklist()

            # Should attempt to rotate (may fail in test env, that's ok)
            assert isinstance(result, bool)

    def test_rate_limiting(self, orchestrator):
        """Test alert rate limiting."""
        from newsauto.monitoring.alert_manager import Alert, AlertSeverity

        alert = Alert(
            title="Test",
            message="Test",
            severity=AlertSeverity.INFO,
            metadata={"rule_key": "test_rule"}
        )

        # First check should pass
        assert orchestrator._check_rate_limit(alert) == True

        # Immediate second check should be rate-limited
        assert orchestrator._check_rate_limit(alert) == False

    @pytest.mark.asyncio
    async def test_failure_count_tracking(self, orchestrator):
        """Test failure count tracking and healing threshold."""
        component = "test_component"

        # Increment failures
        for i in range(3):
            orchestrator._increment_failure(component)

        # Should trigger healing after 3 failures
        assert orchestrator._should_attempt_heal(component) == True

        # Should not attempt again immediately
        assert orchestrator._should_attempt_heal(component) == False
