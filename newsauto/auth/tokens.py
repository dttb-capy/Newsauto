"""Token generation and validation utilities."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import base64

from newsauto.core.config import get_settings

settings = get_settings()


class TokenGenerator:
    """Generate and validate secure tokens."""

    @staticmethod
    def generate_unsubscribe_token(subscriber_id: int, newsletter_id: int) -> str:
        """Generate unsubscribe token for subscriber.

        Args:
            subscriber_id: Subscriber ID
            newsletter_id: Newsletter ID

        Returns:
            Secure unsubscribe token
        """
        # Create payload
        payload = {
            "sub_id": subscriber_id,
            "news_id": newsletter_id,
            "exp": (datetime.utcnow() + timedelta(days=365)).isoformat(),
            "nonce": secrets.token_hex(8)
        }

        # Encode payload
        payload_bytes = json.dumps(payload).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip('=')

        # Create signature
        signature = hmac.new(
            settings.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()[:16]

        return f"{payload_b64}.{signature}"

    @staticmethod
    def validate_unsubscribe_token(token: str) -> Optional[Dict[str, Any]]:
        """Validate unsubscribe token.

        Args:
            token: Token to validate

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Split token
            parts = token.split('.')
            if len(parts) != 2:
                return None

            payload_b64, signature = parts

            # Verify signature
            expected_signature = hmac.new(
                settings.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()[:16]

            if not hmac.compare_digest(signature, expected_signature):
                return None

            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + '==')
            payload = json.loads(payload_bytes)

            # Check expiration
            exp = datetime.fromisoformat(payload['exp'])
            if datetime.utcnow() > exp:
                return None

            return payload

        except Exception:
            return None

    @staticmethod
    def generate_verification_token(email: str) -> str:
        """Generate email verification token.

        Args:
            email: Email address to verify

        Returns:
            Verification token
        """
        payload = {
            "email": email,
            "exp": (datetime.utcnow() + timedelta(hours=48)).isoformat(),
            "nonce": secrets.token_hex(16)
        }

        payload_bytes = json.dumps(payload).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip('=')

        signature = hmac.new(
            settings.secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{payload_b64}.{signature}"

    @staticmethod
    def validate_verification_token(token: str) -> Optional[str]:
        """Validate email verification token.

        Args:
            token: Token to validate

        Returns:
            Email address if valid, None otherwise
        """
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return None

            payload_b64, signature = parts

            # Verify signature
            expected_signature = hmac.new(
                settings.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                return None

            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + '==')
            payload = json.loads(payload_bytes)

            # Check expiration
            exp = datetime.fromisoformat(payload['exp'])
            if datetime.utcnow() > exp:
                return None

            return payload.get('email')

        except Exception:
            return None

    @staticmethod
    def generate_tracking_token(edition_id: int, subscriber_id: int) -> str:
        """Generate tracking token.

        Args:
            edition_id: Edition ID
            subscriber_id: Subscriber ID

        Returns:
            Tracking token
        """
        data = f"{edition_id}:{subscriber_id}:{secrets.token_hex(4)}"
        return hashlib.sha256(f"{data}:{settings.secret_key}".encode()).hexdigest()[:20]

    @staticmethod
    def decode_tracking_token(token: str) -> Optional[Dict[str, int]]:
        """Decode tracking token (note: tokens are one-way hashed, this is for reference).

        Args:
            token: Tracking token

        Returns:
            None (tokens are one-way hashed for security)
        """
        # Tracking tokens are one-way hashed for privacy
        # The actual edition_id and subscriber_id should be stored in database
        # when the token is generated
        return None