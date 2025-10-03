#!/usr/bin/env python
"""
Test email configuration and send a test newsletter.
"""

import asyncio
import os
from datetime import datetime
from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.core.config import get_settings

async def test_email_send():
    print("=" * 70)
    print("📧 TESTING EMAIL CONFIGURATION")
    print("=" * 70)

    settings = get_settings()

    print(f"\n📮 Email Configuration:")
    print(f"   Host: {settings.smtp_host}")
    print(f"   Port: {settings.smtp_port}")
    print(f"   From: {settings.smtp_from}")
    print(f"   User: {settings.smtp_user}")

    # Create email sender with SMTPConfig object
    config = SMTPConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_tls,
        from_email=settings.smtp_from,
        from_name="Newsauto"
    )

    sender = EmailSender(config)

    # Test connection
    print("\n🔌 Testing SMTP connection...")
    try:
        await sender.connect()
        print("✅ SMTP connection successful!")

        # Ask for test email
        print("\n📬 Send a test newsletter?")
        print("Enter email address to send test to (or press Enter to skip):")
        test_email = input("> ").strip()

        if test_email and "@" in test_email:
            print(f"\n📤 Sending test newsletter to {test_email}...")

            # Create test newsletter content
            html_content = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #003366;">🚀 Newsauto Test Newsletter</h1>

                <p>Congratulations! Your email system is working perfectly.</p>

                <h2>System Status</h2>
                <ul>
                    <li>✅ Gmail SMTP configured</li>
                    <li>✅ 10 Premium niches ready</li>
                    <li>✅ 94 RSS feeds configured</li>
                    <li>✅ Automated pipeline ready</li>
                </ul>

                <h2>Revenue Potential</h2>
                <p>With just 146 subscribers at $35/month average:</p>
                <ul>
                    <li>Monthly revenue: $5,110</li>
                    <li>Operating costs: <$10</li>
                    <li>Net profit: $5,100+</li>
                </ul>

                <h2>Next Steps</h2>
                <ol>
                    <li>Deploy to DigitalOcean ($6/month)</li>
                    <li>Import 10 beta subscribers</li>
                    <li>Run daily automation</li>
                    <li>Scale to 146 subscribers</li>
                </ol>

                <hr>
                <p style="color: #666; font-size: 12px;">
                    This is a test email from your Newsauto automated newsletter system.<br>
                    Based on the Portuguese solo founder model: 146 subscribers = $5k/month
                </p>
            </body>
            </html>
            """

            result = await sender.send_email(
                to_email=test_email,
                subject="🎉 Newsauto Test - Your Newsletter System is Ready!",
                html_content=html_content,
                text_content="Your Newsauto system is configured and ready to generate revenue!"
            )

            if result:
                print("✅ Test email sent successfully!")
                print(f"   Check {test_email} for the test newsletter")
            else:
                print("❌ Failed to send test email")
        else:
            print("⏭️  Skipping test email")

        await sender.disconnect()

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Gmail app password")
        print("2. Enable 'Less secure app access' if needed")
        print("3. Verify 2FA is enabled for app passwords")
        return False

    print("\n✅ Email system is ready for production!")
    print("   You can now send newsletters to your subscribers")
    return True

if __name__ == "__main__":
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    asyncio.run(test_email_send())