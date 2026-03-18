# Rate Limiting — v1.0

**Last Updated:** 2026-01-01
**Applies to:** Embedlyzer API v1

---

## Overview

Embedlyzer enforces per-user rate limits on query origination endpoints to prevent runaway costs and ensure fair access.

---

## Limits

| Limit | Default | Applies to |
|-------|---------|------------|
| Hourly query limit | 50 requests / rolling hour | `POST /api/v1/query` |
| Concurrency limit | 5 active streams | `POST /api/v1/query` (open SSE connections) |
| Stream slot TTL | 90 seconds | Orphaned slot cleanup after disconnect |

All defaults are configurable at deployment time via environment variables:

```
RATE_LIMIT_HOURLY=50
CONCURRENCY_LIMIT=5
STREAM_SLOT_TTL=90
```

---

## Response headers

Every response to `POST /api/v1/query` includes rate limit headers:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per hour |
| `X-RateLimit-Remaining` | Remaining requests in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

---

## Rate limit exceeded — `429`

When the limit is reached the server responds with:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 312
Content-Type: application/json

{
  "error": "rate_limit_exceeded",
  "detail": "Quota of 50 requests per hour exceeded. Retry after 312 seconds.",
  "request_id": "req_01hx..."
}
```

The `Retry-After` value is the number of seconds until the oldest request in the rolling window expires.

---

## Concurrency limit exceeded — `429`

When all 5 stream slots are occupied:

```json
{
  "error": "stream_slots_full",
  "detail": "Maximum concurrent streams (5) reached. Close an existing stream before opening a new one.",
  "request_id": "req_01hx..."
}
```

---

## Admin users

Admin users share the same per-user rate limits as regular users. There is no global admin bypass in v1. Contact support to increase limits for operator accounts.

---

## Implementation details

Rate limiting is implemented with a **sliding window counter** stored in Redis.  
Key format: `rl:{user_id}:{window_start_unix_minute}`  
TTL: 3600 seconds.
