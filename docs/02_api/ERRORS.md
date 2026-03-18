# Error Reference — v1.0

**Last Updated:** 2026-01-01
**Applies to:** Embedlyzer API v1

---

## Error response format

All errors return JSON in the following shape:

```json
{
  "error": "string  — machine-readable error code",
  "detail": "string — human-readable explanation",
  "request_id": "string — correlation ID (present when tracing is enabled)"
}
```

---

## HTTP status codes

| Status | When used |
|--------|-----------|
| `400`  | Malformed request (invalid JSON, missing required field) |
| `401`  | Missing or expired JWT |
| `403`  | Valid token but insufficient permissions (wrong role or namespace) |
| `404`  | Resource not found |
| `409`  | Conflict — e.g. duplicate ingest request for the same unreachable ref |
| `422`  | Request schema validation failure (Pydantic) |
| `429`  | Rate limit exceeded (see `Retry-After` header) |
| `500`  | Internal server error |
| `502`  | Upstream service failure (Pinecone, OpenAI) |
| `503`  | Service unavailable — database or vector store not ready |

---

## Error codes

### Authentication / Authorization

| `error` | Status | Meaning |
|---------|--------|---------|
| `authentication_required` | 401 | No `Authorization` header provided |
| `token_expired` | 401 | JWT has passed its `exp` claim |
| `token_invalid` | 401 | JWT signature verification failed |
| `forbidden` | 403 | User lacks required role or namespace grant |

### Query

| `error` | Status | Meaning |
|---------|--------|---------|
| `query_invalid` | 400 | Query text empty or too long |
| `namespace_not_found` | 404 | No vectors exist in the requested namespace |
| `budget_exhausted` | 402 | Monthly token budget has been consumed |
| `stream_slots_full` | 429 | Per-user concurrency limit reached |

### Ingestion

| `error` | Status | Meaning |
|---------|--------|---------|
| `ingest_already_running` | 409 | An ingest run for this repo/branch is already queued or running |
| `ingest_source_not_found` | 404 | The file or repository path does not exist |
| `ingest_connector_error` | 502 | GitHub (or other connector) returned an unrecoverable error |

### Generic

| `error` | Status | Meaning |
|---------|--------|---------|
| `not_found` | 404 | Generic 404 |
| `internal_error` | 500 | Unhandled exception — see server logs for `request_id` |
| `validation_error` | 422 | Pydantic schema validation failure; `detail` lists field errors |

---

## Example: 422 Validation Error

```json
{
  "error": "validation_error",
  "detail": "1 validation error for QueryRequest\nquery_text\n  String should have at least 1 character",
  "request_id": "req_01hx..."
}
```

---

## Streaming errors

For SSE query streams, errors that occur mid-stream are delivered as a final `event: error` frame before the stream closes:

```
event: error
data: {"error":"budget_exhausted","detail":"Monthly token budget has been consumed."}

```
