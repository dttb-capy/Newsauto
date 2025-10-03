# 📡 API Reference

## Overview

The Newsauto API is a RESTful service built with FastAPI that provides programmatic access to all newsletter functionality. The API follows OpenAPI 3.0 specification and includes automatic interactive documentation.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Obtaining a Token

```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the Authorization header:

```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## Endpoints

### Newsletters

#### List All Newsletters

```http
GET /newsletters
```

**Query Parameters:**
- `limit` (int, optional): Number of results (default: 20, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)
- `status` (str, optional): Filter by status (active, paused, draft)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Tech Weekly Digest",
      "niche": "technology",
      "description": "Weekly roundup of tech news",
      "subscriber_count": 1234,
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z",
      "settings": {
        "frequency": "weekly",
        "send_day": "monday",
        "send_time": "08:00"
      }
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

#### Create Newsletter

```http
POST /newsletters
Content-Type: application/json

{
  "name": "AI Research Weekly",
  "niche": "artificial-intelligence",
  "description": "Latest AI research and breakthroughs",
  "template_id": 1,
  "settings": {
    "frequency": "weekly",
    "send_day": "friday",
    "send_time": "09:00",
    "max_articles": 10,
    "summary_length": 150
  }
}
```

**Response:**
```json
{
  "id": 2,
  "name": "AI Research Weekly",
  "niche": "artificial-intelligence",
  "status": "draft",
  "created_at": "2024-01-20T14:30:00Z"
}
```

#### Get Newsletter Details

```http
GET /newsletters/{newsletter_id}
```

**Response:**
```json
{
  "id": 1,
  "name": "Tech Weekly Digest",
  "niche": "technology",
  "description": "Weekly roundup of tech news",
  "subscriber_count": 1234,
  "open_rate": 45.2,
  "click_rate": 12.8,
  "status": "active",
  "created_at": "2024-01-15T10:00:00Z",
  "last_sent": "2024-01-29T08:00:00Z",
  "settings": {
    "frequency": "weekly",
    "send_day": "monday",
    "send_time": "08:00",
    "sources": ["hackernews", "reddit", "techcrunch"],
    "llm_model": "mistral:7b-instruct"
  }
}
```

#### Update Newsletter

```http
PUT /newsletters/{newsletter_id}
Content-Type: application/json

{
  "name": "Tech Weekly Digest - Premium",
  "settings": {
    "max_articles": 15
  }
}
```

#### Delete Newsletter

```http
DELETE /newsletters/{newsletter_id}
```

### Subscribers

#### List Subscribers

```http
GET /subscribers
```

**Query Parameters:**
- `newsletter_id` (int, optional): Filter by newsletter
- `status` (str, optional): active, unsubscribed, bounced
- `segment` (str, optional): Filter by segment
- `search` (str, optional): Search by email or name

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "email": "subscriber@example.com",
      "name": "John Doe",
      "status": "active",
      "segments": ["premium", "tech-enthusiast"],
      "subscribed_at": "2024-01-10T12:00:00Z",
      "preferences": {
        "frequency": "weekly",
        "topics": ["ai", "web3", "security"]
      },
      "stats": {
        "emails_received": 10,
        "emails_opened": 8,
        "links_clicked": 15
      }
    }
  ],
  "total": 1234,
  "limit": 20,
  "offset": 0
}
```

#### Add Subscriber

```http
POST /subscribers
Content-Type: application/json

{
  "email": "new@example.com",
  "name": "Jane Smith",
  "newsletter_ids": [1, 2],
  "segments": ["premium"],
  "preferences": {
    "frequency": "weekly",
    "topics": ["ai", "security"]
  }
}
```

**Response:**
```json
{
  "id": 1235,
  "email": "new@example.com",
  "status": "pending_confirmation",
  "confirmation_sent": true
}
```

#### Update Subscriber

```http
PUT /subscribers/{subscriber_id}
Content-Type: application/json

{
  "preferences": {
    "frequency": "daily",
    "topics": ["ai", "web3", "security", "cloud"]
  }
}
```

#### Unsubscribe

```http
POST /subscribers/{subscriber_id}/unsubscribe

{
  "reason": "too_many_emails",
  "feedback": "Great content but too frequent"
}
```

### Content Management

#### Fetch Content

```http
POST /content/fetch

{
  "sources": ["hackernews", "reddit", "rss"],
  "limit": 100,
  "since": "2024-01-29T00:00:00Z"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "items_queued": 100
}
```

#### List Content Items

```http
GET /content
```

**Query Parameters:**
- `source` (str, optional): Filter by source
- `status` (str, optional): processed, pending, failed
- `min_score` (float, optional): Minimum relevance score
- `since` (datetime, optional): Content after this date

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "url": "https://example.com/article",
      "title": "Breaking: Major AI Breakthrough",
      "source": "hackernews",
      "score": 95.5,
      "summary": "Researchers have achieved...",
      "published_at": "2024-01-29T14:00:00Z",
      "processed_at": "2024-01-29T14:05:00Z",
      "tags": ["ai", "research", "breakthrough"]
    }
  ],
  "total": 250,
  "limit": 20,
  "offset": 0
}
```

#### Get Content Item

```http
GET /content/{content_id}
```

**Response:**
```json
{
  "id": 1,
  "url": "https://example.com/article",
  "title": "Breaking: Major AI Breakthrough",
  "source": "hackernews",
  "score": 95.5,
  "full_text": "Full article content...",
  "summary": "Researchers have achieved...",
  "llm_model": "mistral:7b-instruct",
  "processing_time_ms": 1234,
  "metadata": {
    "author": "Dr. Smith",
    "comments": 234,
    "upvotes": 1500
  }
}
```

### Newsletter Editions

#### Generate Edition

```http
POST /editions/generate

{
  "newsletter_id": 1,
  "test_mode": false,
  "content_filters": {
    "min_score": 80,
    "max_age_hours": 168,
    "topics": ["ai", "security"]
  }
}
```

**Response:**
```json
{
  "edition_id": 123,
  "newsletter_id": 1,
  "status": "draft",
  "content_count": 10,
  "preview_url": "/editions/123/preview"
}
```

#### Preview Edition

```http
GET /editions/{edition_id}/preview
```

Returns HTML preview of the newsletter.

#### Send Edition

```http
POST /editions/{edition_id}/send

{
  "test_recipients": ["test@example.com"],
  "schedule_time": "2024-01-30T08:00:00Z"
}
```

**Response:**
```json
{
  "edition_id": 123,
  "status": "scheduled",
  "recipient_count": 1234,
  "scheduled_time": "2024-01-30T08:00:00Z"
}
```

#### Get Edition Stats

```http
GET /editions/{edition_id}/stats
```

**Response:**
```json
{
  "edition_id": 123,
  "sent_at": "2024-01-30T08:00:00Z",
  "stats": {
    "sent": 1234,
    "delivered": 1230,
    "opened": 567,
    "clicked": 234,
    "unsubscribed": 2,
    "bounced": 4
  },
  "rates": {
    "delivery_rate": 99.7,
    "open_rate": 46.1,
    "click_rate": 19.0,
    "unsubscribe_rate": 0.2
  },
  "top_links": [
    {
      "url": "https://example.com/article1",
      "clicks": 89
    }
  ]
}
```

### Analytics

#### Dashboard Overview

```http
GET /analytics/overview
```

**Query Parameters:**
- `period` (str): day, week, month, year
- `newsletter_id` (int, optional): Specific newsletter

**Response:**
```json
{
  "period": "week",
  "subscribers": {
    "total": 1234,
    "new": 45,
    "unsubscribed": 3,
    "growth_rate": 3.65
  },
  "engagement": {
    "emails_sent": 1234,
    "average_open_rate": 45.2,
    "average_click_rate": 12.8
  },
  "content": {
    "articles_processed": 500,
    "articles_sent": 70,
    "average_score": 85.3
  },
  "llm_usage": {
    "summaries_generated": 500,
    "tokens_processed": 125000,
    "average_response_time_ms": 234
  }
}
```

#### Subscriber Growth

```http
GET /analytics/growth
```

**Query Parameters:**
- `start_date` (date): Start of period
- `end_date` (date): End of period
- `granularity` (str): day, week, month

**Response:**
```json
{
  "data": [
    {
      "date": "2024-01-29",
      "subscribers": 1234,
      "new": 12,
      "unsubscribed": 1
    }
  ]
}
```

### System

#### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "ollama": "connected",
    "email": "connected"
  },
  "uptime_seconds": 86400
}
```

#### System Stats

```http
GET /system/stats
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "resources": {
    "cpu_percent": 23.5,
    "memory_mb": 512,
    "gpu_memory_mb": 4096,
    "disk_usage_gb": 2.3
  },
  "queue": {
    "content_pending": 12,
    "emails_queued": 45
  },
  "cache": {
    "llm_cache_size_mb": 128,
    "hit_rate": 78.5
  }
}
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid input parameters |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

API requests are rate-limited per API key:

- **Standard**: 100 requests per minute
- **Bulk operations**: 10 requests per minute
- **Content fetching**: 5 requests per minute

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706533200
```

## Webhooks

Configure webhooks to receive real-time notifications:

### Webhook Events

- `subscriber.created` - New subscriber confirmed
- `subscriber.unsubscribed` - Subscriber unsubscribed
- `edition.sent` - Newsletter edition sent
- `content.processed` - Content batch processed

### Webhook Payload

```json
{
  "event": "subscriber.created",
  "timestamp": "2024-01-29T14:30:00Z",
  "data": {
    "subscriber_id": 1234,
    "email": "new@example.com",
    "newsletter_id": 1
  }
}
```

## SDK Examples

### Python

```python
import requests

class NewsautoAPI:
    def __init__(self, api_key):
        self.base_url = "http://localhost:8000/api/v1"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def list_newsletters(self):
        response = requests.get(
            f"{self.base_url}/newsletters",
            headers=self.headers
        )
        return response.json()

    def create_subscriber(self, email, newsletter_id):
        response = requests.post(
            f"{self.base_url}/subscribers",
            headers=self.headers,
            json={
                "email": email,
                "newsletter_ids": [newsletter_id]
            }
        )
        return response.json()

# Usage
api = NewsautoAPI("your-api-key")
newsletters = api.list_newsletters()
```

### JavaScript

```javascript
class NewsautoAPI {
  constructor(apiKey) {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }

  async listNewsletters() {
    const response = await fetch(`${this.baseURL}/newsletters`, {
      headers: this.headers
    });
    return response.json();
  }

  async createSubscriber(email, newsletterId) {
    const response = await fetch(`${this.baseURL}/subscribers`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        email: email,
        newsletter_ids: [newsletterId]
      })
    });
    return response.json();
  }
}

// Usage
const api = new NewsautoAPI('your-api-key');
const newsletters = await api.listNewsletters();
```

### cURL

```bash
# List newsletters
curl -X GET "http://localhost:8000/api/v1/newsletters" \
  -H "Authorization: Bearer your-api-key"

# Create subscriber
curl -X POST "http://localhost:8000/api/v1/subscribers" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "new@example.com",
    "newsletter_ids": [1]
  }'

# Generate newsletter edition
curl -X POST "http://localhost:8000/api/v1/editions/generate" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "newsletter_id": 1,
    "test_mode": false
  }'
```

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Versioning

The API uses URL versioning. The current version is `v1`. When breaking changes are introduced, a new version will be created (e.g., `/api/v2`).

## Support

For API support:
- GitHub Issues: [github.com/yourusername/newsauto/issues](https://github.com/yourusername/newsauto/issues)
- API Status: Check `/health` endpoint
- Documentation: This document and interactive docs at `/docs`