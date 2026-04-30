# Agent Webhook Subscriptions - Phase 2 Part 3

Complete implementation of webhook subscription endpoints for the OppGrid Agent API.

## Overview

This implementation adds a webhook subscription system that allows external agents to subscribe to real-time OppGrid events and receive HTTP callbacks when events occur.

**Features:**
- ✅ POST `/api/v1/agents/webhooks/subscribe` - Create webhook subscriptions
- ✅ GET `/api/v1/agents/webhooks` - List active subscriptions
- ✅ DELETE `/api/v1/agents/webhooks/{subscription_id}` - Deactivate subscriptions
- ✅ POST `/api/v1/agents/webhooks/test` - Test webhook delivery
- ✅ Async webhook delivery with exponential backoff retry logic
- ✅ Event filtering by vertical and city
- ✅ Rate limiting (1000 qpm, max 10 webhooks per API key)
- ✅ HTTPS validation and URL testing before saving
- ✅ Secure URL storage with hashing
- ✅ Automatic exponential backoff on failures
- ✅ Background job for webhook delivery
- ✅ Comprehensive error tracking and logging

## Files Modified/Created

### Models
- `backend/app/models/agent_webhook_subscription.py` - NEW: Webhook subscription model
- `backend/app/models/__init__.py` - MODIFIED: Added AgentWebhookSubscription import

### Migrations
- `backend/alembic/versions/20260430_0001_add_agent_webhook_subscriptions.py` - NEW: Database schema migration

### Schemas
- `backend/app/schemas/agent_api.py` - NEW: Request/response schemas for webhook endpoints

### Services
- `backend/app/services/webhook_delivery_service.py` - NEW: Webhook delivery with retry logic
- `backend/app/services/job_runner.py` - MODIFIED: Added webhook_delivery_job

### Routers
- `backend/app/routers/agent.py` - MODIFIED: Added webhook subscription endpoints
- `backend/app/routers/opportunities.py` - MODIFIED: Emit webhook event on opportunity creation

### Tests
- `backend/tests/test_agent_webhooks.py` - NEW: Comprehensive test suite

## Database Schema

### `agent_webhook_subscriptions` Table

```sql
CREATE TABLE agent_webhook_subscriptions (
    subscription_id UUID PRIMARY KEY,
    agent_api_key_id VARCHAR(255) NOT NULL,
    webhook_url TEXT NOT NULL,
    webhook_url_hash VARCHAR(64) UNIQUE,
    events JSONB NOT NULL,  -- ["opportunity.new", "trend.updated", "market.changed"]
    vertical_filter VARCHAR(100),  -- Optional: filter by vertical
    city_filter VARCHAR(100),      -- Optional: filter by city
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    failure_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    user_agent VARCHAR(255)
);

-- Indexes
CREATE INDEX ix_agent_webhook_subscriptions_agent_api_key_id ON agent_webhook_subscriptions(agent_api_key_id);
CREATE INDEX ix_agent_webhook_subscriptions_active ON agent_webhook_subscriptions(active);
CREATE INDEX ix_agent_webhook_subscriptions_created_at ON agent_webhook_subscriptions(created_at);
CREATE UNIQUE INDEX ix_agent_webhook_subscriptions_webhook_url_hash ON agent_webhook_subscriptions(webhook_url_hash);
```

## API Endpoints

### 1. Subscribe to Webhooks

**POST** `/api/v1/agents/webhooks/subscribe`

**Headers:**
```
X-Agent-Key: <your-agent-api-key>
Content-Type: application/json
```

**Request Body:**
```json
{
  "webhook_url": "https://agent.example.com/webhook",
  "events": ["opportunity.new", "trend.updated", "market.changed"],
  "vertical": "coffee",
  "city": "Austin"
}
```

**Response (201 Created):**
```json
{
  "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "events_subscribed": ["opportunity.new", "trend.updated", "market.changed"],
  "created_at": "2026-04-30T02:15:00Z",
  "webhook_url_masked": "https://ag***am/webhook",
  "filters": {
    "vertical": "coffee",
    "city": "Austin"
  }
}
```

**Validation Rules:**
- `webhook_url` must start with `https://`
- `webhook_url` must be valid and respond within 2 seconds
- `events` must contain valid event types: `opportunity.new`, `trend.updated`, `market.changed`
- Max 10 active subscriptions per API key
- Max 1 subscription request per second per key (rate limited)
- Duplicate URLs for the same key are rejected

**Error Responses:**
```json
// HTTPS required
{
  "detail": "webhook_url must use HTTPS protocol"
}

// URL not responding
{
  "detail": "Webhook URL did not respond within 2 seconds"
}

// Max webhooks reached
{
  "detail": "Maximum 10 active webhooks per API key. Deactivate unused webhooks first."
}

// Duplicate URL
{
  "detail": "Webhook URL already subscribed with this API key"
}
```

### 2. List Webhooks

**GET** `/api/v1/agents/webhooks`

**Headers:**
```
X-Agent-Key: <your-agent-api-key>
```

**Response (200 OK):**
```json
{
  "subscriptions": [
    {
      "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "active",
      "events_subscribed": ["opportunity.new"],
      "created_at": "2026-04-30T02:15:00Z",
      "webhook_url_masked": "https://ag***am/webhook",
      "filters": null
    }
  ],
  "total": 1
}
```

### 3. Delete/Deactivate Webhook

**DELETE** `/api/v1/agents/webhooks/{subscription_id}`

**Headers:**
```
X-Agent-Key: <your-agent-api-key>
```

**Response (200 OK):**
```json
{
  "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "deleted",
  "message": "Webhook subscription deactivated"
}
```

### 4. Test Webhook

**POST** `/api/v1/agents/webhooks/test`

**Headers:**
```
X-Agent-Key: <your-agent-api-key>
Content-Type: application/json
```

**Request Body:**
```json
{
  "subscription_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "subscription_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Test event delivered"
}
```

## Webhook Event Payloads

### Event Types

#### 1. `opportunity.new`
Fired when a new opportunity is created.

```json
{
  "event_type": "opportunity.new",
  "timestamp": "2026-04-30T02:15:00Z",
  "data": {
    "opportunity_id": 123,
    "title": "Coffee Shop in Austin",
    "vertical": "coffee",
    "city": "Austin, TX",
    "market_size": 15000000
  },
  "metadata": {
    "agent_id": "agent_xyz",
    "api_version": "v1",
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
    "subscription_id": "sub_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### 2. `trend.updated`
Fired when a market trend is detected or updated.

```json
{
  "event_type": "trend.updated",
  "timestamp": "2026-04-30T02:15:00Z",
  "data": {
    "trend_id": 456,
    "title": "Rising Coffee Shop Demand",
    "vertical": "coffee",
    "city": "Austin, TX",
    "confidence": 0.85
  },
  "metadata": {
    "agent_id": "agent_xyz",
    "api_version": "v1",
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
    "subscription_id": "sub_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### 3. `market.changed`
Fired when market data is updated (demographics, growth, etc.).

```json
{
  "event_type": "market.changed",
  "timestamp": "2026-04-30T02:15:00Z",
  "data": {
    "market_id": 789,
    "city": "Austin, TX",
    "population_growth": 0.05,
    "median_income": 75000
  },
  "metadata": {
    "agent_id": "agent_xyz",
    "api_version": "v1",
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000",
    "subscription_id": "sub_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Webhook Delivery Behavior

### Request Format
All webhook events are delivered as **HTTP POST** requests with:

**Headers:**
```
Content-Type: application/json
X-OppGrid-Event: <event_type>
X-OppGrid-Delivery: <delivery-id>
```

**Body:** JSON payload (see Event Payloads above)

### Expected Response
Your webhook endpoint should return **HTTP 200** status code within **10 seconds** to confirm successful delivery.

```bash
# ✓ Good
curl -X POST https://your-webhook.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"event_type": "opportunity.new", ...}' \
  && echo "200 OK"

# ✗ Bad (will retry)
curl -X POST https://your-webhook.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"event_type": "opportunity.new", ...}' \
  && echo "500 Server Error"
```

### Retry Logic

If your webhook endpoint doesn't return 200 within 10 seconds:

1. **Attempt 1:** Immediate delivery
2. **Attempt 2:** Wait 5 seconds, retry
3. **Attempt 3:** Wait 10 seconds, retry
4. **Attempt 4:** Wait 20 seconds, retry

After 3 failed attempts (4 total tries), the webhook is marked as failed. After 10 consecutive failures, the subscription is automatically **deactivated** and will not receive future events.

### Exponential Backoff Formula
```
backoff_seconds = min(5 * 2^(attempt - 1), 300)
```

- Attempt 1: 5 seconds
- Attempt 2: 10 seconds
- Attempt 3: 20 seconds
- Attempt 4+: Capped at 300 seconds (5 minutes)

## Security Considerations

### 1. HTTPS Only
All webhook URLs must use HTTPS. HTTP URLs are rejected at subscription time.

### 2. URL Validation
Before saving a subscription, we:
- Test the URL with a HEAD request
- Verify it responds within 2 seconds
- Reject invalid/unreachable URLs

### 3. URL Storage
- Webhook URLs are stored in plaintext (consider encrypting in production)
- URLs are hashed (SHA-256) for deduplication checking
- Masked URLs are returned in API responses (first 8 + last 8 characters visible)

### 4. Rate Limiting
- **Global:** 1000 requests per minute (entire agent API)
- **Per Key:** Max 1 subscription request per second
- **Per Key:** Max 10 active webhooks

## Background Job

The `webhook_delivery_job` runs every 60 seconds to:
- Check for subscriptions that need delivery
- Monitor failed webhooks
- Clean up inactive subscriptions
- Log delivery statistics

## Integration Examples

### Python Example
```python
import requests
import json

API_KEY = "your_agent_api_key"
BASE_URL = "https://oppgrid.example.com/api/v1/agent"

# Subscribe to webhook
response = requests.post(
    f"{BASE_URL}/webhooks/subscribe",
    headers={"X-Agent-Key": API_KEY},
    json={
        "webhook_url": "https://your-agent.com/webhook",
        "events": ["opportunity.new"],
        "vertical": "coffee",
        "city": "Austin"
    }
)

subscription = response.json()
print(f"Subscription ID: {subscription['subscription_id']}")

# List webhooks
response = requests.get(
    f"{BASE_URL}/webhooks",
    headers={"X-Agent-Key": API_KEY}
)

webhooks = response.json()
print(f"Active webhooks: {webhooks['total']}")

# Test webhook
response = requests.post(
    f"{BASE_URL}/webhooks/test",
    headers={"X-Agent-Key": API_KEY},
    json={"subscription_id": subscription['subscription_id']}
)

print(f"Test successful: {response.json()['success']}")

# Delete webhook
response = requests.delete(
    f"{BASE_URL}/webhooks/{subscription['subscription_id']}",
    headers={"X-Agent-Key": API_KEY}
)

print(f"Deleted: {response.json()['status']}")
```

### cURL Examples
```bash
# Subscribe
curl -X POST https://oppgrid.example.com/api/v1/agent/webhooks/subscribe \
  -H "X-Agent-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-agent.com/webhook",
    "events": ["opportunity.new"],
    "vertical": "coffee"
  }'

# List
curl -X GET https://oppgrid.example.com/api/v1/agent/webhooks \
  -H "X-Agent-Key: your_api_key"

# Test
curl -X POST https://oppgrid.example.com/api/v1/agent/webhooks/test \
  -H "X-Agent-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"subscription_id": "550e8400-e29b-41d4-a716-446655440000"}'

# Delete
curl -X DELETE https://oppgrid.example.com/api/v1/agent/webhooks/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-Agent-Key: your_api_key"
```

## Testing

Run the test suite:
```bash
cd backend
pytest tests/test_agent_webhooks.py -v
```

Test Coverage:
- ✅ Webhook subscription creation with validation
- ✅ HTTPS enforcement
- ✅ Event type validation
- ✅ Max webhooks per key
- ✅ URL masking for security
- ✅ Hash generation for deduplication
- ✅ Webhook delivery with retry logic
- ✅ Exponential backoff calculation
- ✅ Event emission with filtering

## Deployment Steps

1. **Apply database migration:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Verify schema:**
   ```bash
   psql $DATABASE_URL -c "\dt agent_webhook_subscriptions"
   ```

3. **Start the application:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Test endpoints:**
   ```bash
   curl -X GET http://localhost:8000/api/v1/agent/webhooks \
     -H "X-Agent-Key: test_key"
   ```

## Monitoring

Monitor webhook delivery:
```sql
-- Active subscriptions
SELECT COUNT(*) FROM agent_webhook_subscriptions WHERE active = true;

-- Failed subscriptions (marked inactive)
SELECT COUNT(*) FROM agent_webhook_subscriptions WHERE active = false AND failure_count >= 10;

-- Recent deliveries
SELECT 
  subscription_id,
  last_triggered_at,
  failure_count,
  last_error
FROM agent_webhook_subscriptions
ORDER BY last_triggered_at DESC
LIMIT 10;

-- Webhooks by vertical
SELECT 
  vertical_filter,
  COUNT(*) as count,
  AVG(failure_count) as avg_failures
FROM agent_webhook_subscriptions
WHERE active = true
GROUP BY vertical_filter;
```

## Known Limitations

1. **Webhook URL Encryption:** URLs are stored in plaintext. Consider implementing field-level encryption for production.

2. **Webhook Queue:** Current implementation delivers webhooks synchronously. For high-volume events, consider adding a persistent queue (e.g., Redis).

3. **Event Filtering:** Filtering by vertical/city is done in Python. Consider moving to database-level filtering for performance.

4. **Delivery Guarantees:** Webhooks are "at least once" (with retries). Implement idempotency in your webhook handler.

5. **Event History:** No persistent event log for debugging/replay. Consider adding an `event_log` table for audit trails.

## Future Enhancements

- [ ] Event replay for failed deliveries
- [ ] Webhook signature verification (HMAC-SHA256)
- [ ] Custom headers in webhook requests
- [ ] Event filtering by additional criteria (status, score, etc.)
- [ ] Webhook delivery metrics dashboard
- [ ] Dead letter queue for permanently failed webhooks
- [ ] Webhook authentication (Basic Auth, Bearer token)
- [ ] Conditional delivery (only if market_size > X)

## Support

For issues or questions about webhook subscriptions:
1. Check the test suite: `tests/test_agent_webhooks.py`
2. Review error logs in `last_error` field
3. Use the test endpoint to verify webhook connectivity
4. Monitor `failure_count` and `last_failure_at` for troubleshooting

---

**Implementation Date:** April 30, 2026
**Status:** ✅ Complete - Ready for Phase 1 Integration Testing
