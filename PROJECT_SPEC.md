# Newsauto Project Specification

**Version**: 1.0.0
**Date**: January 2024
**Status**: Development

## Executive Summary

Newsauto is a zero-cost, fully automated newsletter platform that leverages local Large Language Models (LLMs) to aggregate, summarize, and distribute high-quality content to targeted micro-niche audiences. The system is designed to scale from 0 to 1000+ subscribers with zero operational costs by utilizing local GPU resources and free-tier services.

## Project Goals

### Primary Objectives
1. **Zero Operating Costs**: Run entirely on local hardware with free services
2. **Full Automation**: Minimal human intervention after initial setup
3. **High-Quality Content**: LLM-powered summarization and curation
4. **Scalability**: Handle 1000+ subscribers without infrastructure changes
5. **Privacy-First**: All data processing happens locally

### Success Metrics
- Generate and send daily/weekly newsletters automatically
- Process 100+ articles per minute
- Achieve >40% open rates
- Maintain <$1/month operating costs
- Support 10+ different newsletter niches simultaneously

## Functional Requirements

### Content Aggregation (F1)

#### F1.1 Multi-Source Support
- **RSS Feeds**: Parse standard RSS/Atom feeds
- **Reddit API**: Fetch posts from specified subreddits
- **HackerNews**: Access HN API for top stories
- **Web Scraping**: Extract content from arbitrary websites
- **APIs**: Integrate with content provider APIs

#### F1.2 Content Processing
- Fetch content on configurable schedules
- Deduplicate articles using content hashing
- Score content relevance (0-100 scale)
- Extract metadata (author, date, tags)
- Handle multiple content formats (text, HTML, Markdown)

#### F1.3 Content Filtering
- Filter by keywords and topics
- Exclude blacklisted sources
- Minimum/maximum content length
- Language detection and filtering
- Time-based filtering (recency)

### LLM Integration (F2)

#### F2.1 Model Support
- Ollama integration for local models
- Support for Mistral, Llama, DeepSeek, Qwen
- HuggingFace Transformers compatibility
- Model routing based on content type
- Fallback chain for reliability

#### F2.2 Summarization
- Generate concise summaries (50-500 words)
- Extract key points and insights
- Maintain context and accuracy
- Adapt tone for target audience
- Support multiple summary styles

#### F2.3 Content Enhancement
- Generate engaging headlines
- Create section introductions
- Add contextual commentary
- Identify trends across articles
- Generate calls-to-action

### Newsletter Generation (F3)

#### F3.1 Content Selection
- Select top N articles by score
- Balance content categories
- Respect subscriber preferences
- Ensure content diversity
- Handle content quotas

#### F3.2 Template System
- HTML and plain text templates
- Responsive email design
- Variable substitution
- Conditional content blocks
- A/B testing support

#### F3.3 Personalization
- Per-subscriber content selection
- Dynamic content blocks
- Preference-based filtering
- Engagement-based optimization
- Name and location personalization

### Subscriber Management (F4)

#### F4.1 Registration
- Double opt-in process
- Email verification
- Preference collection
- Welcome email series
- GDPR compliance

#### F4.2 Segmentation
- Automatic segmentation by behavior
- Manual segment creation
- Dynamic segment updates
- Segment-based campaigns
- Cross-segment analytics

#### F4.3 Preference Management
- Self-service preference center
- Frequency controls
- Topic preferences
- Content type selection
- Pause/resume subscriptions

### Email Delivery (F5)

#### F5.1 Sending Infrastructure
- SMTP integration (Gmail, custom)
- API integration (SendGrid, Resend)
- Batch sending capabilities
- Send time optimization
- Rate limiting

#### F5.2 Deliverability
- SPF/DKIM/DMARC setup
- Bounce handling
- Complaint processing
- List hygiene
- Reputation monitoring

#### F5.3 Tracking
- Open rate tracking
- Click tracking
- Unsubscribe tracking
- Forward tracking
- Device/client analytics

### Analytics & Reporting (F6)

#### F6.1 Performance Metrics
- Subscriber growth tracking
- Engagement metrics (open/click)
- Content performance
- Revenue tracking
- LLM usage statistics

#### F6.2 Dashboards
- Real-time metrics dashboard
- Historical trends
- Comparative analysis
- Export capabilities
- Custom reports

#### F6.3 Insights
- Automated insights generation
- Anomaly detection
- Predictive analytics
- Churn prediction
- Content recommendations

### Automation (F7)

#### F7.1 Scheduling
- Cron-based scheduling
- Time zone handling
- Holiday awareness
- Optimal send time calculation
- Retry mechanisms

#### F7.2 Workflows
- Content fetch → Process → Send pipeline
- Error handling and recovery
- Notification system
- Backup processes
- Archive generation

#### F7.3 Maintenance
- Automatic cache cleanup
- Database optimization
- Log rotation
- Performance monitoring
- Health checks

## Non-Functional Requirements

### Performance (N1)
- **Content Processing**: <5 seconds for 100 articles
- **LLM Summarization**: <1 second per article
- **Newsletter Generation**: <30 seconds total
- **API Response Time**: <200ms p95
- **Email Sending**: 1000 emails/minute

### Scalability (N2)
- Support 10,000+ subscribers
- Handle 1,000+ articles/day
- Process 10+ newsletters concurrently
- Horizontal scaling capability
- Database partitioning support

### Reliability (N3)
- 99.9% uptime for core services
- Automatic failure recovery
- Data backup every 6 hours
- Zero data loss guarantee
- Graceful degradation

### Security (N4)
- Encrypted data at rest
- Secure API authentication (JWT)
- Rate limiting on all endpoints
- SQL injection prevention
- XSS protection

### Usability (N5)
- Setup in <30 minutes
- No coding required for basic use
- Intuitive admin interface
- Comprehensive documentation
- Error messages with solutions

### Compatibility (N6)
- Python 3.12+ support
- Linux/macOS/Windows compatibility
- SQLite and PostgreSQL support
- Modern browser support
- Mobile-responsive interface

## Technical Specifications

### Technology Stack

#### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0
- **Task Queue**: Python asyncio / Celery
- **Testing**: pytest, coverage

#### LLM Infrastructure
- **Server**: Ollama
- **Models**: Mistral 7B, DeepSeek R1, Llama 3.2
- **Frameworks**: Transformers, LangChain
- **GPU**: CUDA 11.8+

#### Frontend
- **Framework**: Vanilla JS / React (optional)
- **Styling**: Tailwind CSS
- **Charts**: Chart.js
- **Tables**: DataTables

#### Database
- **Development**: SQLite
- **Production**: PostgreSQL 15+
- **Cache**: File-based / Redis
- **Search**: Full-text search

#### Infrastructure
- **Container**: Docker
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus/Grafana
- **Logging**: structlog

### System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Content Sources│────▶│   Scrapers   │────▶│  Deduplicator│
└─────────────────┘     └──────────────┘     └──────────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   LLM Router    │◀────│Content Scorer│◀────│Content Cache │
└─────────────────┘     └──────────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Mistral/Llama  │────▶│  Newsletter  │────▶│   Template   │
│   DeepSeek/Phi  │     │  Generator   │     │    Engine    │
└─────────────────┘     └──────────────┘     └──────────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scheduler     │────▶│Email Delivery│────▶│   Tracking   │
└─────────────────┘     └──────────────┘     └──────────────┘
```

### API Specification

#### RESTful Endpoints
```
GET    /api/v1/newsletters
POST   /api/v1/newsletters
GET    /api/v1/newsletters/{id}
PUT    /api/v1/newsletters/{id}
DELETE /api/v1/newsletters/{id}

GET    /api/v1/subscribers
POST   /api/v1/subscribers
GET    /api/v1/subscribers/{id}
PUT    /api/v1/subscribers/{id}
DELETE /api/v1/subscribers/{id}

POST   /api/v1/content/fetch
GET    /api/v1/content
GET    /api/v1/content/{id}

POST   /api/v1/editions/generate
POST   /api/v1/editions/{id}/send
GET    /api/v1/editions/{id}/preview

GET    /api/v1/analytics/overview
GET    /api/v1/analytics/growth
GET    /api/v1/analytics/engagement
```

### Database Schema

#### Core Tables
- newsletters (id, name, niche, settings)
- subscribers (id, email, preferences, status)
- content_items (id, url, title, content, summary)
- editions (id, newsletter_id, content, sent_at)
- subscriber_events (id, type, metadata, timestamp)

#### Indexes
- content_items(score, published_at)
- subscribers(email, status)
- editions(newsletter_id, sent_at)

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Project setup and structure
- [ ] Database schema implementation
- [ ] Basic CRUD operations
- [ ] Ollama integration
- [ ] Simple content fetching

### Phase 2: Content Pipeline (Week 2)
- [ ] RSS feed parser
- [ ] Reddit/HN integration
- [ ] Content deduplication
- [ ] LLM summarization
- [ ] Content scoring

### Phase 3: Newsletter System (Week 3)
- [ ] Newsletter generation
- [ ] Template engine
- [ ] Email sending (SMTP)
- [ ] Subscriber management
- [ ] Basic personalization

### Phase 4: Automation (Week 4)
- [ ] Scheduling system
- [ ] GitHub Actions setup
- [ ] Error handling
- [ ] Monitoring
- [ ] Testing suite

### Phase 5: Polish (Week 5)
- [ ] Admin dashboard
- [ ] Analytics
- [ ] Documentation
- [ ] Performance optimization
- [ ] Deployment

## Testing Strategy

### Unit Testing
- Model validation
- Utility functions
- Business logic
- API endpoints
- LLM integration

### Integration Testing
- Database operations
- Content pipeline
- Email delivery
- External APIs
- Cache layer

### End-to-End Testing
- Complete newsletter flow
- Subscriber journey
- Admin workflows
- Error scenarios
- Performance tests

### Test Coverage Goals
- Overall: 80%
- Critical paths: 100%
- API endpoints: 90%
- Business logic: 85%

## Deployment Strategy

### Development
```bash
# Local development
python main.py --dev
```

### Staging
```bash
# Docker deployment
docker-compose up -d
```

### Production
```yaml
# GitHub Actions
on:
  schedule:
    - cron: '0 8 * * *'
```

## Monitoring & Maintenance

### Key Metrics
- System health (CPU, memory, disk)
- Application metrics (requests, errors)
- Business metrics (subscribers, emails)
- LLM metrics (tokens, latency)

### Alerts
- Service downtime
- High error rates
- Low delivery rates
- Disk space warnings
- Performance degradation

### Maintenance Tasks
- Daily: Check logs, monitor metrics
- Weekly: Database backup, cache cleanup
- Monthly: Performance review, updates
- Quarterly: Security audit, major updates

## Risk Analysis

### Technical Risks
- **LLM Model Updates**: May break compatibility
  - *Mitigation*: Version pinning, extensive testing

- **GPU Memory Limitations**: OOM errors
  - *Mitigation*: Batch size optimization, model selection

- **Email Deliverability**: Spam filters
  - *Mitigation*: Proper authentication, list hygiene

### Business Risks
- **Content Quality**: Poor summaries
  - *Mitigation*: Quality scoring, human review option

- **Subscriber Churn**: High unsubscribe rates
  - *Mitigation*: Personalization, frequency controls

- **Scaling Costs**: Growing beyond free tiers
  - *Mitigation*: Efficient resource usage, gradual monetization

## Success Criteria

### Launch (Month 1)
- ✓ System fully operational
- ✓ 3 active newsletters
- ✓ 100 total subscribers
- ✓ 90% delivery rate

### Growth (Month 3)
- ✓ 10 active newsletters
- ✓ 500 total subscribers
- ✓ 40% average open rate
- ✓ First paid sponsor

### Scale (Month 6)
- ✓ 25 active newsletters
- ✓ 2000 total subscribers
- ✓ $1000 MRR
- ✓ Full automation

## Future Enhancements

### Version 2.0
- Mobile application
- Advanced personalization
- Multi-language support
- Voice newsletter option
- SMS delivery

### Version 3.0
- AI content generation
- Predictive analytics
- Automated A/B testing
- Social media integration
- Podcast generation

## Appendices

### A. Glossary
- **LLM**: Large Language Model
- **MRR**: Monthly Recurring Revenue
- **CTR**: Click-Through Rate
- **ESP**: Email Service Provider

### B. References
- [Ollama Documentation](https://ollama.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Email Best Practices](https://www.emailvendorselection.com)

### C. License
MIT License - See LICENSE file for details

---

*This specification is a living document and will be updated as the project evolves.*