# Zero-Intervention Automation Setup Guide

Complete setup guide for achieving **true zero-intervention operation** with automated quality control, self-healing infrastructure, and comprehensive alerting.

## Table of Contents
1. [Quick Start](#quick-start)
2. [GitHub Projects Board Setup](#github-projects-board-setup)
3. [Quality Control Pipeline](#quality-control-pipeline)
4. [Self-Healing Infrastructure](#self-healing-infrastructure)
5. [Alert System Configuration](#alert-system-configuration)
6. [Testing & Validation](#testing--validation)
7. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Quick Start

### 1. Database Migration
```bash
# Apply quality score schema changes
make migrate-quality
# or
alembic upgrade head
```

### 2. Run Initial Quality Check
```bash
# Check recent content quality
make quality-check

# Generate detailed report
make quality-report
```

### 3. Test Self-Healing
```bash
# Run comprehensive health checks
make self-heal-check

# Test self-healing mechanisms
make self-heal-test
```

### 4. Test Alerts
```bash
# Send test alert
make alert-test

# View recent alerts
make alert-history
```

---

## GitHub Projects Board Setup

### Option 1: Automated Setup via GitHub Actions

1. **Create GitHub Project Board**:
   ```bash
   # Go to your repo on GitHub
   # Click "Projects" → "New project" → "Board"
   # Copy the project URL (e.g., https://github.com/users/YOUR_USERNAME/projects/1)
   ```

2. **Set Repository Secrets**:
   ```bash
   # In repo Settings → Secrets and variables → Actions
   # Add these secrets:
   - PROJECT_URL: Your project board URL
   - GH_PROJECT_TOKEN: GitHub PAT with repo & project permissions
   ```

3. **Trigger Milestone Creation**:
   ```bash
   # Manually run the workflow once
   gh workflow run project-sync.yml
   ```

### Option 2: Use /board Command

```bash
# In Claude Code
/board

# Shows ASCII visualization like:
┌────────────────────────────────────────┐
│     NEWSAUTO DEVELOPMENT BOARD         │
└────────────────────────────────────────┘

PHASE 1: FOUNDATION [████████████] 100% ✓
├─ [✓] Project setup
├─ [✓] Database schema
...
```

### Workflow Files Created

1. **`.github/workflows/project-sync.yml`**
   - Syncs issues/PRs to project board
   - Auto-labels based on Conventional Commits
   - Creates milestones from PROJECT_SPEC phases

2. **`.github/workflows/update-board.yml`**
   - Updates board on push/merge
   - Tracks commit → task relationships
   - Celebrates milestone completions

---

## Quality Control Pipeline

### Architecture

```
Daily @ 8am UTC (GitHub Actions)
      ↓
Sample 10% of content (last 24h)
      ↓
Run Quality Scoring:
  • Hallucination Detection (40%)
  • Factual Accuracy (35%)
  • Sentiment Analysis (25%)
      ↓
Aggregate Score (0.0 - 1.0)
      ↓
Flag if < 0.85 or issues detected
      ↓
Create GitHub Issue for Review
```

### Files Created

1. **`scripts/quality_score.py`** - Main scoring engine
2. **`newsauto/quality/hallucination_detector.py`** - Detects LLM hallucinations
3. **`newsauto/quality/factual_checker.py`** - Cross-references sources
4. **`newsauto/quality/sentiment_analyzer.py`** - Detects sentiment bias
5. **`.github/workflows/content-quality-check.yml`** - Daily automated checks
6. **`alembic/versions/*_add_quality_scores_to_content.py`** - Database schema

### Usage

**Manual Quality Check**:
```bash
# Check recent content (last 1 day)
python scripts/quality_score.py

# Check specific content item
python scripts/quality_score.py --content-id 123

# Generate weekly report
python scripts/quality_score.py --sample-rate 0.20 --days-back 7 --output json
```

**Makefile Commands**:
```bash
make quality-check         # Quick daily check (10% sample)
make quality-report        # Weekly report (20% sample, JSON output)
make quality-content       # Check specific content (prompts for ID)
```

**GitHub Actions**:
- Runs automatically daily at 8am UTC
- Workflow dispatch: Manual trigger with custom sample rate
- Creates issues when quality threshold breached

### Quality Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Overall Quality Score | < 0.75 | Fail build + create issue |
| Hallucination Risk | > 0.20 | Flag for review |
| Factual Accuracy | < 0.70 | Flag for review |
| Sentiment | < -0.30 or > 0.80 | Flag for review |
| Flagged Rate | > 15% | Fail build |

### Database Schema Changes

```sql
-- Added to content_items table:
ALTER TABLE content_items ADD COLUMN quality_score REAL DEFAULT 0.0;
ALTER TABLE content_items ADD COLUMN hallucination_score REAL;
ALTER TABLE content_items ADD COLUMN factual_score REAL;
ALTER TABLE content_items ADD COLUMN sentiment_score REAL;
ALTER TABLE content_items ADD COLUMN confidence_score REAL DEFAULT 1.0;
ALTER TABLE content_items ADD COLUMN needs_review BOOLEAN DEFAULT 0;
ALTER TABLE content_items ADD COLUMN quality_flags JSON;
ALTER TABLE content_items ADD COLUMN quality_checked_at DATETIME;

-- Indexes for performance:
CREATE INDEX ix_content_items_quality_score ON content_items(quality_score);
CREATE INDEX ix_content_items_needs_review ON content_items(needs_review);
```

---

## Self-Healing Infrastructure

### Architecture

```
Continuous Monitoring (every 5 minutes)
      ↓
Health Checks:
  • SMTP (blacklist detection)
  • Ollama (model availability)
  • Feeds (failure rate)
  • Database (connection)
      ↓
Detect Issues
      ↓
Trigger Healing:
  • SMTP → Rotate relay
  • Ollama → Pull models
  • Feeds → Disable failed
  • Database → Restore backup
      ↓
Log + Alert
```

### Files Created

1. **`newsauto/automation/self_heal.py`** - Main orchestrator
2. **`newsauto/monitoring/health_checks.py`** - Specialized health checks

### Components

#### SMTP Self-Healing

**Detects**:
- Blacklisting (keywords in error: "blacklist", "spam", "reputation")
- Connection failures
- Send failures

**Heals**:
1. Detects blacklisting via canary email
2. Rotates to backup relay:
   - SendGrid
   - Resend
   - Gmail Backup
3. Updates configuration
4. Logs rotation event
5. Sends alert

**Recovery Time**: < 30 seconds

#### Ollama Self-Healing

**Detects**:
- Service unavailable
- Missing required models

**Heals**:
1. Checks service availability
2. Pulls missing models
3. Verifies model integrity

**Recovery Time**: < 5 minutes (model download time)

#### Feed Self-Healing

**Detects**:
- 3+ consecutive failures
- >20% overall failure rate

**Heals**:
1. Disables failing feeds temporarily (6 hours)
2. Schedules retry with exponential backoff
3. Alerts if critical feed fails

**Recovery Time**: Immediate (feed disabled)

#### Database Self-Healing

**Detects**:
- Connection failures
- Corruption (integrity check)

**Heals**:
1. Retry connection
2. Restore from latest backup
3. Migrate to PostgreSQL if SQLite limits hit

**Recovery Time**: < 2 minutes

### Usage

**Start Self-Healing Service**:
```bash
# Run as background service
make self-heal-start

# Or integrate into systemd:
# See scripts/systemd/newsauto-self-heal.service
```

**Manual Health Check**:
```bash
make self-heal-check

# Output:
{
  "overall_healthy": true,
  "checks": {
    "smtp": {"healthy": true, ...},
    "ollama": {"healthy": true, ...},
    "feeds": {"healthy": true, ...},
    "database": {"healthy": true, ...}
  }
}
```

**Run Tests**:
```bash
make self-heal-test
pytest tests/test_self_healing.py -v
```

### Configuration

Add to `.env`:
```bash
# SMTP Backup Relays
SMTP_BACKUP_RELAYS='[
  {"name": "SendGrid", "host": "smtp.sendgrid.net"},
  {"name": "Resend", "host": "smtp.resend.com"}
]'

# Health Check Settings
HEALTH_CHECK_INTERVAL=300  # seconds
SMTP_CANARY_EMAIL=test@your-domain.com

# Self-Healing Settings
AUTO_HEAL_ENABLED=true
MAX_HEAL_ATTEMPTS=3
HEAL_COOLDOWN_MINUTES=10
```

---

## Alert System Configuration

### Architecture

```
Event Occurs
    ↓
Alert Created (title, message, severity, component)
    ↓
Check Rate Limit (per rule + global)
    ↓
Route to Channels (based on severity/rule)
    ↓
Send in Parallel:
  • Slack (webhooks)
  • Discord (webhooks)
  • Email (SMTP)
  • PagerDuty (API)
  • Console (logs)
    ↓
Track History + Deduplicate
```

### Files Created

1. **`newsauto/monitoring/alert_manager.py`** - Centralized alerting
2. **`config/alert_rules.yml`** - Alert rules & routing

### Supported Channels

| Channel | Use Case | Config Required |
|---------|----------|-----------------|
| **Slack** | Team notifications | Webhook URL |
| **Discord** | Community alerts | Webhook URL |
| **Email** | Important updates | SMTP config |
| **PagerDuty** | Critical incidents | Integration key |
| **Console** | Development/logs | None (always enabled) |

### Setup Instructions

#### 1. Slack Integration

```bash
# 1. Create Slack App: https://api.slack.com/apps
# 2. Enable Incoming Webhooks
# 3. Add webhook to workspace
# 4. Copy webhook URL

# Add to .env:
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Update config/alert_rules.yml:
channels:
  slack:
    enabled: true
    webhook_url: ${SLACK_WEBHOOK_URL}
```

#### 2. Discord Integration

```bash
# 1. Go to Server Settings → Integrations → Webhooks
# 2. Create webhook for alerts channel
# 3. Copy webhook URL

# Add to .env:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK

# Update config:
channels:
  discord:
    enabled: true
    webhook_url: ${DISCORD_WEBHOOK_URL}
```

#### 3. Email Alerts

```bash
# Already configured if SMTP is set up
# Just enable and specify recipients:

channels:
  email:
    enabled: true
    to:
      - admin@your-domain.com
      - team@your-domain.com
```

#### 4. PagerDuty Integration

```bash
# 1. Go to PagerDuty → Services → New Service
# 2. Integration Type: Events API v2
# 3. Copy Integration Key

# Add to .env:
PAGERDUTY_INTEGRATION_KEY=your_integration_key

# Update config:
channels:
  pagerduty:
    enabled: true
    integration_key: ${PAGERDUTY_INTEGRATION_KEY}
```

### Alert Rules

Example from `config/alert_rules.yml`:

```yaml
rules:
  smtp_blacklisted:
    severity: critical
    channels: [pagerduty, slack, email]
    rate_limit: 300  # 5 minutes
    description: "SMTP server blacklisted"

  low_quality_content:
    severity: warning
    channels: [slack, email]
    rate_limit: 3600  # 1 hour
    description: "Content quality below threshold"
```

### Usage

**Send Custom Alert**:
```python
from newsauto.monitoring.alert_manager import send_alert, AlertSeverity

await send_alert(
    title="Custom Alert",
    message="Something important happened",
    severity=AlertSeverity.WARNING,
    component="my_component",
    rule_key="custom_rule"
)
```

**Makefile Commands**:
```bash
make alert-test       # Send test alert to all channels
make alert-history    # View recent alerts (last 24h)
```

### Alert Severities

| Severity | Use Case | Example |
|----------|----------|---------|
| **critical** | System down, data loss risk | SMTP blacklisted, DB corruption |
| **error** | Feature broken | Ollama model missing, newsletter send failed |
| **warning** | Performance degraded | High error rate, memory usage 85% |
| **info** | Notable events | Self-healing triggered, milestone completed |
| **debug** | Development info | Config changed, test run |

### Rate Limiting

- **Per-rule rate limit**: Prevents spam for specific issues
- **Global rate limit**: Maximum 1 alert per minute across all rules
- **Deduplication**: Same alert within cooldown period is suppressed

Example:
```yaml
# Send max once per hour
rules:
  low_quality_content:
    rate_limit: 3600

# Global: max 1 alert/minute across all rules
global_rate_limit: 60
```

---

## Testing & Validation

### Run All Tests
```bash
# Complete test suite
make test

# Specific systems
pytest tests/test_quality_pipeline.py -v
pytest tests/test_self_healing.py -v
```

### Quality Pipeline Tests
```bash
# Test hallucination detection
pytest tests/test_quality_pipeline.py::TestHallucinationDetector -v

# Test factual checking
pytest tests/test_quality_pipeline.py::TestFactualChecker -v

# Test sentiment analysis
pytest tests/test_quality_pipeline.py::TestSentimentAnalyzer -v
```

### Self-Healing Tests
```bash
# Test SMTP health checks
pytest tests/test_self_healing.py::TestSMTPHealthCheck -v

# Test Ollama health checks
pytest tests/test_self_healing.py::TestOllamaHealthCheck -v

# Test orchestrator
pytest tests/test_self_healing.py::TestSelfHealingOrchestrator -v
```

### Integration Tests
```bash
# End-to-end quality check
python scripts/quality_score.py --sample-rate 0.05 --days-back 1

# End-to-end self-healing
make self-heal-check

# End-to-end alerting
make alert-test
```

---

## Monitoring & Maintenance

### Daily Checks (Automated)

✅ **Automated via GitHub Actions**:
- Quality check runs at 8am UTC daily
- Creates issues if thresholds breached
- Generates metrics in `metrics/quality-history.jsonl`

### Weekly Review (Minimal Human Time)

**10 minutes/week**:
```bash
# 1. Review quality reports (2 min)
make quality-report

# 2. Check alert history (2 min)
make alert-history

# 3. Review flagged content (5 min)
# Open GitHub issues tagged "quality-review"

# 4. Check self-healing stats (1 min)
# Review recent healing events in logs
```

### Monthly Maintenance

**30 minutes/month**:
1. Review metrics trends
2. Adjust quality thresholds if needed
3. Update alert rules based on false positive rate
4. Backup configuration files

### Metrics Dashboard

View in Prometheus/Grafana (if configured):
- Quality scores over time
- Alert frequency by type
- Self-healing success rate
- System uptime

---

## Troubleshooting

### Quality Checks Failing

**Issue**: Many false positives

**Solution**:
```yaml
# Adjust thresholds in scripts/quality_score.py
self.min_quality_score = 0.80  # Was 0.85
self.hallucination_threshold = 0.25  # Was 0.20
```

### Self-Healing Not Working

**Issue**: SMTP rotation fails

**Solution**:
```bash
# Check backup relay credentials
# Verify SMTP_BACKUP_RELAYS in .env
# Test manually:
python -c "from newsauto.monitoring.health_checks import SMTPHealthCheck; \
import asyncio; print(asyncio.run(SMTPHealthCheck().check()))"
```

### Alerts Not Sending

**Issue**: No alerts received

**Solution**:
```bash
# 1. Check channel configuration
cat config/alert_rules.yml

# 2. Test specific channel
make alert-test

# 3. Check logs for errors
tail -f logs/newsauto.log | grep -i alert
```

---

## Success Metrics

### Target Metrics (After 4 Weeks)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Human Intervention** | Daily | Zero (except flagged reviews) | 🎯 |
| **Uptime** | 95% | 99%+ | 🎯 |
| **Quality Issues Caught** | Manual | 90% automated | 🎯 |
| **MTTR** | Manual | <5 min automated | 🎯 |
| **Development Visibility** | Text logs | Visual Kanban | 🎯 |

### Weekly Reporting

Automated report generated weekly with:
- Quality score trends
- Self-healing activations
- Alert summary
- System uptime
- Recommendations

---

## Next Steps

1. **Enable GitHub Actions**:
   - Set up project board
   - Configure secrets
   - Test workflows

2. **Configure Alerts**:
   - Set up Slack/Discord webhooks
   - Test each channel
   - Tune rate limits

3. **Start Self-Healing**:
   - Run as systemd service
   - Monitor for 1 week
   - Adjust thresholds

4. **Monitor & Iterate**:
   - Review weekly metrics
   - Adjust based on false positive/negative rates
   - Document learnings

---

## Support & Resources

- **Documentation**: https://github.com/yourusername/newsauto/docs
- **Issues**: https://github.com/yourusername/newsauto/issues
- **Claude Code**: Use `/board` command for status visualization

**Key Files Reference**:
- Quality: `scripts/quality_score.py`
- Self-Healing: `newsauto/automation/self_heal.py`
- Alerts: `newsauto/monitoring/alert_manager.py`
- Configuration: `config/alert_rules.yml`
- Tests: `tests/test_quality_pipeline.py`, `tests/test_self_healing.py`
