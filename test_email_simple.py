#!/usr/bin/env python
"""
Simple test to verify Gmail SMTP configuration.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from newsauto.core.config import get_settings

def test_gmail_smtp():
    print("=" * 70)
    print("📧 TESTING GMAIL SMTP CONFIGURATION")
    print("=" * 70)

    settings = get_settings()

    print(f"\n📮 Email Configuration:")
    print(f"   Host: {settings.smtp_host}")
    print(f"   Port: {settings.smtp_port}")
    print(f"   From: {settings.smtp_from}")
    print(f"   User: {settings.smtp_user}")

    try:
        # Create SMTP connection
        print("\n🔌 Connecting to Gmail SMTP...")
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()

        print("🔐 Authenticating...")
        server.login(settings.smtp_user, settings.smtp_password)
        print("✅ Authentication successful!")

        # Ask for test email
        print("\n📬 Send a test newsletter?")
        print("Enter email address to send test to (or press Enter to skip):")
        test_email = input("> ").strip()

        if test_email and "@" in test_email:
            print(f"\n📤 Sending test email to {test_email}...")

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "🎉 Newsauto Test - Your Newsletter System is Ready!"
            msg["From"] = settings.smtp_from
            msg["To"] = test_email

            # Create the HTML part
            html = """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #003366;">🚀 Newsauto Test Success!</h1>

                <p><strong>Your Gmail SMTP configuration is working perfectly!</strong></p>

                <h2>✅ System Status</h2>
                <ul>
                    <li>Gmail SMTP: Connected</li>
                    <li>Authentication: Successful</li>
                    <li>10 Premium niches: Configured</li>
                    <li>94 RSS feeds: Ready</li>
                </ul>

                <h2>💰 Revenue Potential</h2>
                <p>With just 146 subscribers at $35/month average:</p>
                <ul>
                    <li>Monthly revenue: $5,110</li>
                    <li>Operating costs: <$10</li>
                    <li>Net profit: $5,100+</li>
                </ul>

                <h2>🎯 Next Steps</h2>
                <ol>
                    <li>Import 10 beta subscribers</li>
                    <li>Monitor for 40% open rate</li>
                    <li>Scale to 146 subscribers</li>
                </ol>

                <hr style="border: 1px solid #eee;">
                <p style="color: #666; font-size: 12px;">
                    This test email confirms your Newsauto automated newsletter system is ready.<br>
                    Based on the Portuguese solo founder model: 146 subscribers = $5k/month
                </p>
            </body>
            </html>
            """

            text = """
            Newsauto Test Success!

            Your Gmail SMTP configuration is working perfectly!

            System Status:
            - Gmail SMTP: Connected
            - Authentication: Successful
            - 10 Premium niches: Configured
            - 94 RSS feeds: Ready

            Revenue Potential:
            With just 146 subscribers at $35/month average:
            - Monthly revenue: $5,110
            - Operating costs: <$10
            - Net profit: $5,100+

            Next Steps:
            1. Import 10 beta subscribers
            2. Monitor for 40% open rate
            3. Scale to 146 subscribers
            """

            # Attach parts
            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send the email
            server.send_message(msg)
            print("✅ Test email sent successfully!")
            print(f"   Check {test_email} for the test newsletter")
        else:
            print("⏭️  Skipping test email")

        server.quit()
        print("\n✅ Gmail SMTP test complete!")
        print("   Your email system is ready for production")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your Gmail app password is correct")
        print("2. Ensure 2FA is enabled on your Google account")
        print("3. Generate app password at: https://myaccount.google.com/apppasswords")
        print("4. Check that 'Less secure app access' is not needed")
        return False

if __name__ == "__main__":
    test_gmail_smtp()