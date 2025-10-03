# 🚀 Newsauto Production Deployment Guide

## Based on Portuguese Founder's <$5/month Architecture

This guide will help you deploy your 10-niche automated newsletter platform to production, following the proven low-cost model.

## 📊 Current Status
- ✅ 10 Premium niches configured
- ✅ Content pipeline automated
- ✅ 65/25/10 content ratio management
- ✅ 94 RSS feeds configured
- ✅ Subscriber segmentation ready
- ⏳ SMTP configuration needed
- ⏳ Database setup needed
- ⏳ Hosting deployment needed

## 🏗️ Architecture Overview

```
DigitalOcean Droplet ($6/month)
├── Newsauto Application (Python/FastAPI)
├── PostgreSQL Database
├── Ollama (Local LLM)
├── Listmonk (Email ESP) - Optional
└── n8n (Automation) - Optional

GitHub Actions (Free)
└── Daily automation triggers
```

## 1️⃣ Quick Start (Development → Beta)

### Step 1: Configure Email Delivery

```bash
# Option A: Gmail (Quick start, free up to 500 emails/day)
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-specific-password  # Generate at https://myaccount.google.com/apppasswords

# Option B: SendGrid (Free tier: 100 emails/day)
export SMTP_HOST=smtp.sendgrid.net
export SMTP_PORT=587
export SMTP_USERNAME=apikey
export SMTP_PASSWORD=your-sendgrid-api-key

# Option C: AWS SES (Cheapest at scale: $0.10 per 1000 emails)
export SMTP_HOST=email-smtp.us-east-1.amazonaws.com
export SMTP_PORT=587
export SMTP_USERNAME=your-ses-smtp-username
export SMTP_PASSWORD=your-ses-smtp-password
```

### Step 2: Set Up Database (Production)

```bash
# Local development (already set up)
export DATABASE_URL=sqlite:///./data/newsletter.db

# Production PostgreSQL (recommended)
export DATABASE_URL=postgresql://user:password@localhost:5432/newsauto

# Run migrations
alembic upgrade head
```

### Step 3: Configure Ollama Models

```bash
# Install Ollama (if not installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull mistral:7b-instruct  # Primary model
ollama pull deepseek-r1:1.5b      # Fast fallback
ollama pull phi-3                 # Lightweight option

# Verify
ollama list
```

### Step 4: Test the Pipeline

```bash
# Test content fetching for a niche
python -c "
from newsauto.automation.full_pipeline import AutomatedNewsletterPipeline
import asyncio

async def test():
    pipeline = AutomatedNewsletterPipeline()
    # This will run in test mode (no actual emails sent)
    await pipeline.run_daily_pipeline()

asyncio.run(test())
"
```

## 2️⃣ Production Deployment (DigitalOcean - $6/month)

### Create Droplet

```bash
# 1. Create DigitalOcean droplet
# - Choose Ubuntu 24.04 LTS
# - Select $6/month plan (1GB RAM, 25GB SSD)
# - Add SSH key

# 2. SSH into droplet
ssh root@your-droplet-ip

# 3. Clone repository
git clone https://github.com/yourusername/newsauto.git
cd newsauto

# 4. Install dependencies
apt update && apt upgrade -y
apt install python3.11 python3-pip postgresql nginx certbot python3-certbot-nginx -y

# 5. Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral:7b-instruct

# 7. Set up PostgreSQL
sudo -u postgres psql
CREATE DATABASE newsauto;
CREATE USER newsauto WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE newsauto TO newsauto;
\q

# 8. Configure environment
cp .env.example .env
nano .env  # Add your configurations

# 9. Run migrations
alembic upgrade head

# 10. Set up systemd service
sudo nano /etc/systemd/system/newsauto.service
```

### Systemd Service Configuration

```ini
[Unit]
Description=Newsauto Newsletter Platform
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/newsauto
Environment="PATH=/root/newsauto/venv/bin"
ExecStart=/root/newsauto/venv/bin/python -m uvicorn newsauto.api.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable newsauto
sudo systemctl start newsauto
```

### Set Up Daily Automation

```bash
# Option 1: Cron job
crontab -e

# Add this line for daily execution at 9 AM EST
0 14 * * * cd /root/newsauto && /root/newsauto/venv/bin/python -m newsauto.automation.full_pipeline >> /var/log/newsauto.log 2>&1

# Option 2: GitHub Actions (free)
# Create .github/workflows/daily-newsletter.yml
```

## 3️⃣ Import Initial Subscribers

### Create Subscriber Import Script

```python
# import_subscribers.py
import asyncio
from newsauto.core.database import get_db
from newsauto.models.subscriber import Subscriber

async def import_subscribers():
    # Your initial 100 hand-picked executives
    subscribers = [
        {"email": "cto@techcompany.com", "name": "John Doe", "company": "TechCo", "role": "CTO"},
        # Add more...
    ]

    async with get_db() as db:
        for sub_data in subscribers:
            subscriber = Subscriber(**sub_data)
            db.add(subscriber)
        await db.commit()

asyncio.run(import_subscribers())
```

## 4️⃣ Monitoring & Analytics

### Set Up Monitoring

```bash
# Install monitoring tools
pip install prometheus-client

# Add to your code
from prometheus_client import Counter, Histogram, start_http_server

# Track metrics
newsletters_sent = Counter('newsletters_sent', 'Total newsletters sent')
open_rate = Histogram('open_rate', 'Newsletter open rates')
```

### Check Daily Logs

```bash
# View automation logs
tail -f /var/log/newsauto.log

# Check API logs
journalctl -u newsauto -f

# Monitor resource usage
htop
```

## 5️⃣ Launch Checklist

### Pre-Launch (Beta - 100 subscribers)

- [ ] SMTP configured and tested
- [ ] Database migrated and backed up
- [ ] Ollama models downloaded
- [ ] RSS feeds verified (at least 5 working per niche)
- [ ] Test newsletter sent successfully
- [ ] Daily automation scheduled
- [ ] Error notifications configured
- [ ] Backup strategy in place

### Week 1-2: Soft Launch

1. **Import 10-20 friendly contacts**
   ```bash
   python import_subscribers.py --batch friendly
   ```

2. **Monitor metrics**
   - Open rates (target: 40%)
   - Click rates (target: 10%)
   - Unsubscribes (target: <2%)

3. **Iterate on content**
   - Adjust RSS feeds based on engagement
   - Tune AI prompts for better summaries
   - Test different send times

### Week 3-4: Beta Launch (100 subscribers)

1. **Strategic outreach**
   - LinkedIn: Target CTOs at Series A-D startups
   - Twitter: Engage with tech leadership
   - HackerNews: Share insights (not promotional)

2. **Pricing activation**
   - Enable Stripe integration
   - Set up pricing tiers
   - Create upgrade flow

### Month 2: Scale to 146+ (Portuguese model target)

1. **Growth tactics**
   - Referral program (3 months free for referrals)
   - Guest posts on engineering blogs
   - Speaking at virtual CTO meetups

2. **Optimize for profitability**
   - Target: 146 paying subscribers
   - Revenue: ~$5,000/month
   - Costs: <$10/month (hosting + tools)

## 6️⃣ Cost Optimization Tips

### Keep it under $10/month

1. **Hosting**: DigitalOcean $6 droplet
2. **Email**: Gmail free tier or AWS SES ($1/month for 10k emails)
3. **Database**: PostgreSQL on same droplet (free)
4. **LLM**: Ollama local (free) or GPT-4o-mini ($2/month)
5. **Monitoring**: Self-hosted Prometheus (free)
6. **Backups**: DigitalOcean snapshots ($1/month)

**Total: $8-10/month for complete infrastructure**

## 7️⃣ Emergency Procedures

### If emails aren't sending
```bash
# Check SMTP connection
python -c "
from newsauto.email.email_sender import EmailSender
sender = EmailSender({'smtp_host': 'smtp.gmail.com', ...})
sender.test_connection()
"
```

### If content fetch fails
```bash
# Test RSS feeds
python test_niche_content.py

# Manually trigger for specific niche
python -m newsauto.scrapers.niche_aggregator
```

### If Ollama crashes
```bash
# Restart Ollama
sudo systemctl restart ollama

# Check status
ollama list
```

## 8️⃣ Success Metrics

### Week 1 Targets
- ✅ 10 subscribers onboarded
- ✅ 40% open rate achieved
- ✅ Daily automation running
- ✅ All 10 niches tested

### Month 1 Targets
- ✅ 100 subscribers acquired
- ✅ 10% conversion to paid
- ✅ $350 MRR achieved
- ✅ <$10/month costs maintained

### Month 3 Targets (Portuguese Model)
- ✅ 146+ paying subscribers
- ✅ $5,000+ MRR
- ✅ 40% open rate maintained
- ✅ Fully automated (0 hours/week)

## 🎯 Ready to Launch!

You now have everything needed to launch your automated newsletter empire:

1. **Start with Gmail SMTP** (quick, free)
2. **Deploy to DigitalOcean** ($6/month)
3. **Import 10 beta users** (friends/colleagues)
4. **Monitor for 1 week**
5. **Scale to 100 users**
6. **Activate monetization**
7. **Reach Portuguese model metrics** (146 subscribers, $5k/month)

---

**Remember**: The Portuguese founder succeeded with just 146 subscribers. Focus on quality over quantity, and the premium C-suite audience will pay for valuable, curated insights.

**Support**: Open an issue on GitHub or check the logs at `/var/log/newsauto.log`