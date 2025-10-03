"""Unsubscribe and preference management endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from newsauto.auth.tokens import TokenGenerator
from newsauto.core.database import get_db
from newsauto.models.subscriber import Subscriber, NewsletterSubscriber
from newsauto.models.events import SubscriberEvent, EventType

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


@router.get("", response_class=HTMLResponse)
async def unsubscribe_page(
    token: str = Query(..., description="Unsubscribe token"),
    db: Session = Depends(get_db)
) -> str:
    """Display unsubscribe confirmation page.

    Args:
        token: Unsubscribe token
        db: Database session

    Returns:
        HTML page
    """
    # Validate token
    payload = TokenGenerator.validate_unsubscribe_token(token)
    if not payload:
        return _error_page("Invalid or expired unsubscribe link")

    subscriber_id = payload["sub_id"]
    newsletter_id = payload["news_id"]

    # Get subscriber
    subscriber = db.query(Subscriber).filter(Subscriber.id == subscriber_id).first()
    if not subscriber:
        return _error_page("Subscriber not found")

    # Get newsletter subscription
    subscription = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.subscriber_id == subscriber_id,
            NewsletterSubscriber.newsletter_id == newsletter_id
        )
        .first()
    )

    if not subscription:
        return _error_page("Subscription not found")

    if subscription.unsubscribed_at:
        return _success_page("You are already unsubscribed from this newsletter")

    # Return confirmation page
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unsubscribe</title>
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
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                line-height: 1.6;
            }}
            .button {{
                display: inline-block;
                padding: 12px 24px;
                background: #dc3545;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .button:hover {{
                background: #c82333;
            }}
            .secondary {{
                background: #6c757d;
            }}
            .secondary:hover {{
                background: #5a6268;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Confirm Unsubscribe</h1>
            <p>Hello {subscriber.name or 'there'},</p>
            <p>Are you sure you want to unsubscribe from our newsletter?</p>
            <p>You'll no longer receive updates and valuable content.</p>

            <form method="post" action="/unsubscribe/confirm">
                <input type="hidden" name="token" value="{token}">
                <button type="submit" class="button">Yes, Unsubscribe Me</button>
            </form>

            <p>Changed your mind?
            <a href="/preferences?token={token}" class="secondary button">
                Manage Preferences Instead
            </a></p>

            <p style="margin-top: 40px; font-size: 14px; color: #999;">
                If you didn't request this, you can safely ignore this page.
            </p>
        </div>
    </body>
    </html>
    """


@router.post("/confirm")
async def confirm_unsubscribe(
    token: str = Query(..., description="Unsubscribe token"),
    db: Session = Depends(get_db)
) -> Response:
    """Confirm unsubscribe action.

    Args:
        token: Unsubscribe token
        db: Database session

    Returns:
        Success response
    """
    # Validate token
    payload = TokenGenerator.validate_unsubscribe_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    subscriber_id = payload["sub_id"]
    newsletter_id = payload["news_id"]

    # Get subscription
    subscription = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.subscriber_id == subscriber_id,
            NewsletterSubscriber.newsletter_id == newsletter_id
        )
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.unsubscribed_at:
        return HTMLResponse(_success_page("Already unsubscribed"))

    # Unsubscribe
    subscription.unsubscribed_at = datetime.utcnow()

    # Log event
    event = SubscriberEvent(
        subscriber_id=subscriber_id,
        event_type=EventType.UNSUBSCRIBED,
        metadata={"newsletter_id": newsletter_id, "method": "link"}
    )
    db.add(event)

    db.commit()

    return HTMLResponse(_success_page("You have been successfully unsubscribed"))


@router.post("/one-click")
async def one_click_unsubscribe(
    token: str = Query(..., description="Unsubscribe token"),
    db: Session = Depends(get_db)
) -> dict:
    """One-click unsubscribe (RFC 8058).

    Args:
        token: Unsubscribe token
        db: Database session

    Returns:
        JSON response
    """
    # Validate token
    payload = TokenGenerator.validate_unsubscribe_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid token")

    subscriber_id = payload["sub_id"]
    newsletter_id = payload["news_id"]

    # Get subscription
    subscription = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.subscriber_id == subscriber_id,
            NewsletterSubscriber.newsletter_id == newsletter_id
        )
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not subscription.unsubscribed_at:
        subscription.unsubscribed_at = datetime.utcnow()

        # Log event
        event = SubscriberEvent(
            subscriber_id=subscriber_id,
            event_type=EventType.UNSUBSCRIBED,
            metadata={"newsletter_id": newsletter_id, "method": "one-click"}
        )
        db.add(event)
        db.commit()

    return {"status": "unsubscribed", "message": "Successfully unsubscribed"}


@router.get("/resubscribe")
async def resubscribe(
    token: str = Query(..., description="Unsubscribe token"),
    db: Session = Depends(get_db)
) -> Response:
    """Resubscribe to newsletter.

    Args:
        token: Unsubscribe token (reused for resubscribe)
        db: Database session

    Returns:
        Success response
    """
    # Validate token
    payload = TokenGenerator.validate_unsubscribe_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    subscriber_id = payload["sub_id"]
    newsletter_id = payload["news_id"]

    # Get subscription
    subscription = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.subscriber_id == subscriber_id,
            NewsletterSubscriber.newsletter_id == newsletter_id
        )
        .first()
    )

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if not subscription.unsubscribed_at:
        return HTMLResponse(_success_page("You are already subscribed"))

    # Resubscribe
    subscription.unsubscribed_at = None

    # Log event
    event = SubscriberEvent(
        subscriber_id=subscriber_id,
        event_type=EventType.SUBSCRIBED,
        metadata={"newsletter_id": newsletter_id, "method": "resubscribe"}
    )
    db.add(event)

    db.commit()

    return HTMLResponse(_success_page("Welcome back! You have been resubscribed"))


def _success_page(message: str) -> str:
    """Generate success page HTML.

    Args:
        message: Success message

    Returns:
        HTML page
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Success</title>
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
                font-size: 48px;
                color: #28a745;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✓</div>
            <h1>Success!</h1>
            <p>{message}</p>
            <p style="margin-top: 40px;">
                <a href="/" style="color: #007bff;">Return to homepage</a>
            </p>
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
        <title>Error</title>
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
            }}
            .icon {{
                font-size: 48px;
                color: #dc3545;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">⚠</div>
            <h1>Error</h1>
            <p>{message}</p>
            <p style="margin-top: 40px;">
                <a href="/" style="color: #007bff;">Return to homepage</a>
            </p>
        </div>
    </body>
    </html>
    """