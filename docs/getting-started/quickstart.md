# 🚀 Quickstart Guide

Get your first automated newsletter running in 15 minutes!

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.12+ installed
- ✅ NVIDIA GPU with 8GB+ VRAM
- ✅ 20GB free disk space
- ✅ Internet connection for initial setup

Quick check:
```bash
python3 --version  # Should show 3.12 or higher
nvidia-smi         # Should show your GPU
```

## 5-Minute Setup

### Step 1: One-Line Installation

```bash
# Clone and setup in one command
curl -fsSL https://raw.githubusercontent.com/yourusername/newsauto/main/scripts/quickstart.sh | bash
```

Or manually:
```bash
git clone https://github.com/yourusername/newsauto.git
cd newsauto
./scripts/setup.sh
```

### Step 2: Quick Configuration

```bash
# Run interactive setup
python scripts/quick_config.py
```

This will ask you for:
1. Newsletter name (e.g., "Tech Weekly")
2. Your email for testing
3. Content sources (just press Enter for defaults)

### Step 3: Test Run

```bash
# Generate your first newsletter
python scripts/test_newsletter.py

# Check the output
cat output/test_newsletter.html
```

## Your First Real Newsletter (10 minutes)

### 1. Start the Application

```bash
# Start Newsauto
python main.py

# In another terminal, check it's running
curl http://localhost:8000/health
```

### 2. Create a Newsletter

Open your browser to http://localhost:8000

Or use the CLI:
```bash
python scripts/create_newsletter.py \
    --name "AI Weekly Digest" \
    --niche "artificial-intelligence" \
    --email "your-email@gmail.com"
```

### 3. Add Content Sources

```python
# scripts/add_sources.py
from newsauto import ContentSource

# Add HackerNews
ContentSource.create(
    name="HackerNews AI",
    type="hackernews",
    config={
        "keywords": ["AI", "machine learning", "LLM"],
        "min_score": 50
    }
)

# Add Reddit
ContentSource.create(
    name="r/MachineLearning",
    type="reddit",
    config={
        "subreddit": "MachineLearning",
        "sort": "hot",
        "limit": 25
    }
)

# Add RSS Feed
ContentSource.create(
    name="MIT AI News",
    type="rss",
    config={
        "url": "https://news.mit.edu/rss/topic/artificial-intelligence"
    }
)
```

### 4. Fetch and Process Content

```bash
# Fetch content from all sources
python -c "from newsauto import fetch_all_content; fetch_all_content()"

# Check what was fetched
python -c "from newsauto import Content; print(f'Fetched {Content.count()} articles')"
```

### 5. Generate Newsletter

```bash
# Generate newsletter with AI summaries
python -c "
from newsauto import Newsletter, generate_edition
newsletter = Newsletter.get(1)
edition = generate_edition(newsletter)
print(f'Generated edition with {len(edition.content)} articles')
"
```

### 6. Preview and Send

```bash
# Preview in browser
python -c "
from newsauto import Edition
edition = Edition.get_latest()
edition.preview()  # Opens in browser
"

# Send test email to yourself
python -c "
from newsauto import Edition
edition = Edition.get_latest()
edition.send_test('your-email@gmail.com')
"
```

## Quick Examples

### Example 1: Tech Newsletter

```python
# create_tech_newsletter.py
from newsauto import Newsletter, ContentSource

# Create newsletter
newsletter = Newsletter.create(
    name="Tech Daily",
    niche="technology",
    settings={
        "frequency": "daily",
        "send_time": "08:00",
        "max_articles": 10
    }
)

# Add sources
sources = [
    ("HackerNews", "hackernews", {"min_score": 100}),
    ("r/programming", "reddit", {"subreddit": "programming"}),
    ("TechCrunch", "rss", {"url": "https://techcrunch.com/feed/"})
]

for name, type, config in sources:
    ContentSource.create(
        name=name,
        type=type,
        newsletter_id=newsletter.id,
        config=config
    )

print(f"Created {newsletter.name} with {len(sources)} sources")
```

### Example 2: AI Research Newsletter

```python
# create_ai_newsletter.py
from newsauto import Newsletter, ContentSource

newsletter = Newsletter.create(
    name="AI Research Weekly",
    niche="ai-research",
    settings={
        "frequency": "weekly",
        "send_day": "monday",
        "llm_model": "deepseek-r1:7b",  # Better for technical content
        "summary_style": "technical"
    }
)

# Add academic sources
sources = [
    ("arXiv AI", "rss", {"url": "http://arxiv.org/rss/cs.AI"}),
    ("r/MachineLearning", "reddit", {"subreddit": "MachineLearning"}),
    ("Papers with Code", "web", {"url": "https://paperswithcode.com/latest"})
]

for name, type, config in sources:
    ContentSource.create(name=name, type=type, config=config)
```

### Example 3: Business Newsletter

```python
# create_business_newsletter.py
from newsauto import Newsletter

newsletter = Newsletter.create(
    name="Startup Weekly",
    niche="startups",
    settings={
        "frequency": "weekly",
        "topics": ["funding", "growth", "product"],
        "exclude_topics": ["crypto"],
        "min_score": 80
    }
)
```

## Automation Setup

### Option 1: Local Cron (Linux/macOS)

```bash
# Add to crontab
crontab -e

# Add this line for daily at 8 AM
0 8 * * * cd /path/to/newsauto && python scripts/daily_newsletter.py

# Add this line for weekly on Mondays
0 8 * * 1 cd /path/to/newsauto && python scripts/weekly_newsletter.py
```

### Option 2: GitHub Actions (Free)

Create `.github/workflows/newsletter.yml`:

```yaml
name: Daily Newsletter
on:
  schedule:
    - cron: '0 13 * * *'  # 8 AM EST
  workflow_dispatch:      # Manual trigger

jobs:
  send_newsletter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          curl -fsSL https://ollama.com/install.sh | sh
          ollama pull mistral:7b-instruct

      - name: Generate and send newsletter
        env:
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
        run: |
          python scripts/daily_newsletter.py
```

### Option 3: Systemd Service (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/newsauto.service

# Add this content:
[Unit]
Description=Newsauto Newsletter Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/newsauto
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable newsauto
sudo systemctl start newsauto
```

## Quick Commands Reference

```bash
# System commands
python main.py                    # Start the application
python scripts/check_health.py    # Check system health
python scripts/test_email.py      # Test email configuration

# Newsletter management
python scripts/list_newsletters.py
python scripts/create_newsletter.py --name "Name" --niche "niche"
python scripts/delete_newsletter.py --id 1

# Content management
python scripts/fetch_content.py --source all
python scripts/list_content.py --limit 10
python scripts/score_content.py

# Subscriber management
python scripts/add_subscriber.py --email "email@example.com"
python scripts/import_subscribers.py --file subscribers.csv
python scripts/export_subscribers.py --newsletter-id 1

# Newsletter generation
python scripts/generate_newsletter.py --newsletter-id 1
python scripts/send_newsletter.py --edition-id 1
python scripts/send_test.py --email "test@example.com"

# Analytics
python scripts/show_stats.py --newsletter-id 1
python scripts/export_analytics.py --format csv
```

## Quick Troubleshooting

### Issue: Ollama not running
```bash
# Start Ollama
ollama serve

# Or as background service
nohup ollama serve > ollama.log 2>&1 &
```

### Issue: GPU not detected
```bash
# Check CUDA
nvidia-smi

# Reinstall PyTorch with CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Issue: Email not sending
```bash
# Test SMTP connection
python scripts/test_email.py --verbose

# Check settings
cat .env | grep SMTP
```

### Issue: No content found
```bash
# Test individual sources
python scripts/test_source.py --source hackernews
python scripts/test_source.py --source reddit --subreddit technology
```

## Next Steps

1. **Add more sources**: Customize content sources for your niche
2. **Customize templates**: Edit `templates/newsletter.html`
3. **Set up automation**: Choose from cron, GitHub Actions, or systemd
4. **Add subscribers**: Import your email list
5. **Monitor performance**: Check analytics dashboard

## Quick Tips

1. **Start small**: Test with 10 subscribers first
2. **Use test mode**: Always test before sending to all subscribers
3. **Monitor GPU**: Watch GPU memory with `nvidia-smi -l 1`
4. **Check logs**: Logs are in `logs/newsauto.log`
5. **Backup data**: Run `python scripts/backup.py` regularly

## Getting Help

- 📖 [Full Documentation](../index.md)
- 💬 [GitHub Discussions](https://github.com/yourusername/newsauto/discussions)
- 🐛 [Report Issues](https://github.com/yourusername/newsauto/issues)
- 📧 Email: support@newsauto.io

## Example Output

Here's what your first newsletter might look like:

```html
Subject: 🚀 Tech Weekly: AI Breakthrough, New Framework, Security Alert

Hi [Name],

Here are this week's top stories:

1. **Major AI Breakthrough at MIT**
   Researchers demonstrate new model 10x more efficient...
   [Read more →]

2. **FastAPI 1.0 Released**
   The popular Python framework reaches stable version...
   [Read more →]

3. **Critical Security Vulnerability in npm**
   Update your packages immediately to patch...
   [Read more →]

Happy reading!
The Tech Weekly Team
```

---

**Congratulations!** 🎉 You've set up your first automated newsletter. It will now run automatically based on your schedule, fetching content, generating summaries with AI, and sending to your subscribers—all with zero ongoing costs!