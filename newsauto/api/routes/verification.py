"""Email verification endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from newsauto.auth.tokens import TokenGenerator
from newsauto.core.database import get_db
from newsauto.core.config import get_settings
from newsauto.models.subscriber import Subscriber
from newsauto.models.events import SubscriberEvent, EventType
from newsauto.email.email_sender import EmailSender, SMTPConfig

router = APIRouter(prefix="/verify", tags=["verification"])
settings = get_settings()


@router.get("", response_class=HTMLResponse)
async def verify_email(
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db)
) -> str:
    """Verify email address.

    Args:
        token: Verification token
        db: Database session

    Returns:
        HTML page
    """
    # Validate token
    email = TokenGenerator.validate_verification_token(token)
    if not email:
        return _error_page("Invalid or expired verification link")

    # Get subscriber
    subscriber = db.query(Subscriber).filter(Subscriber.email == email).first()
    if not subscriber:
        return _error_page("Email address not found")

    if subscriber.verified_at:
        return _success_page(
            "Email already verified",
            "Your email address has already been verified. You're all set!"
        )

    # Verify email
    subscriber.verified_at = datetime.utcnow()
    subscriber.status = "active"

    # Log event
    event = SubscriberEvent(
        subscriber_id=subscriber.id,
        event_type=EventType.VERIFIED,
        metadata={"method": "email_link"}
    )
    db.add(event)
    db.commit()

    return _success_page(
        "Email Verified!",
        f"Thank you for verifying your email address ({email}). You'll now receive our newsletters!"
    )


@router.post("/resend")
async def resend_verification(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> dict:
    """Resend verification email.

    Args:
        email: Email address
        background_tasks: Background tasks
        db: Database session

    Returns:
        Success response
    """
    # Get subscriber
    subscriber = db.query(Subscriber).filter(Subscriber.email == email).first()
    if not subscriber:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}

    if subscriber.verified_at:
        return {"message": "Email already verified"}

    # Generate new token
    token = TokenGenerator.generate_verification_token(email)
    verification_url = f"{settings.frontend_url}/verify?token={token}"

    # Send verification email in background
    background_tasks.add_task(
        send_verification_email,
        email,
        subscriber.name,
        verification_url
    )

    # Log event
    event = SubscriberEvent(
        subscriber_id=subscriber.id,
        event_type=EventType.VERIFICATION_SENT,
        metadata={"method": "resend"}
    )
    db.add(event)
    db.commit()

    return {"message": "Verification email sent"}


async def send_verification_email(
    email: str,
    name: Optional[str],
    verification_url: str
) -> bool:
    """Send verification email.

    Args:
        email: Recipient email
        name: Recipient name
        verification_url: Verification URL

    Returns:
        Success status
    """
    smtp_config = SMTPConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_tls,
        from_email=settings.smtp_from,
    )

    sender = EmailSender(smtp_config)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #007bff;
                border-bottom: 2px solid #007bff;
                padding-bottom: 10px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .button:hover {{
                background: #0056b3;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                font-size: 14px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Verify Your Email Address</h1>

            <p>Hi {name or 'there'},</p>

            <p>Welcome to our newsletter! Please verify your email address to start receiving our content.</p>

            <p>Click the button below to verify your email:</p>

            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>

            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #007bff;">
                {verification_url}
            </p>

            <p>This link will expire in 48 hours for security reasons.</p>

            <div class="footer">
                <p>If you didn't sign up for our newsletter, you can safely ignore this email.</p>
                <p>Need help? Contact us at support@newsauto.io</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Verify Your Email Address

    Hi {name or 'there'},

    Welcome to our newsletter! Please verify your email address to start receiving our content.

    Click this link to verify your email:
    {verification_url}

    This link will expire in 48 hours for security reasons.

    If you didn't sign up for our newsletter, you can safely ignore this email.

    Need help? Contact us at support@newsauto.io
    """

    try:
        success = await sender.send_email(
            to_email=email,
            subject="Verify Your Email Address",
            html_content=html_content,
            text_content=text_content,
        )
        return success
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def _success_page(title: str, message: str) -> str:
    """Generate success page HTML.

    Args:
        title: Page title
        message: Success message

    Returns:
        HTML page
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h1 {{
                color: #28a745;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                line-height: 1.6;
            }}
            .icon {{
                font-size: 64px;
                color: #28a745;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 20px;
            }}
            .button:hover {{
                background: #0056b3;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✓</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <a href="/" class="button">Go to Homepage</a>
        </div>
    </body>
    </html>
    """


def _error_page(message: str) -> str:
    """Generate error page HTML.

    Args:
        message: Error message

    Returns:
        HTML page
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verification Error</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px;
                margin: 100px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }}
            h1 {{
                color: #dc3545;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                line-height: 1.6;
                margin-bottom: 30px;
            }}
            .icon {{
                font-size: 64px;
                color: #dc3545;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                background: #6c757d;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 5px;
            }}
            .button:hover {{
                background: #5a6268;
            }}
            .primary {{
                background: #007bff;
            }}
            .primary:hover {{
                background: #0056b3;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">⚠</div>
            <h1>Verification Failed</h1>
            <p>{message}</p>
            <p>The verification link may have expired or been used already.</p>
            <a href="/resend-verification" class="button primary">Request New Link</a>
            <a href="/" class="button">Go to Homepage</a>
        </div>
    </body>
    </html>
    """