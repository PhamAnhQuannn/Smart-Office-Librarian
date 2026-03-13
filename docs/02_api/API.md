# API Documentation — v1.0.10 (production-ready)

**Version:** v1.0.10  
**Base URL:** `/api/v1`  
**Protocol:** HTTP streaming with SSE framing (compatible with HTTP/1.1; HTTP/2 permitted if proxies do not buffer)  
**Authentication:** JWT Bearer tokens  
**Last Updated:** 2026-03-11  

> This is a production API contract and operator guidance document (no implementation code). v1.0.10 aligns with backbone documents (ARCHITECTURE.md v1.6, REQUIREMENTS.md v1.5, DECISIONS.md v1.5): rate limit now 50/hour (FR-5.1), chunking specs explicit (512 tokens, 50 overlap), group-based RBAC marked as v2 feature, confidence bands reference backbone requirements.

> **Backbone Alignment Status:** This document is aligned with the current backbone specification. Group-based RBAC (`shared` visibility) is noted as a v2 enhancement not yet specified in backbone documents.

Timestamps in responses **MUST** be ISO 8601 in UTC (use `Z` suffix). All text encoding is UTF-8.

---

# Overview

This document defines the API contract for the Smart Office Librarian RAG system. Endpoints follow REST conventions with JSON payloads and streaming responses for real-time UX. Key system properties:

* **Grounded responses / refusal contract:** system NEVER returns hallucinated answers; when confidence is below configured threshold it returns a refusal (HTTP 200 with `mode="refusal"` and sources).
* **RBAC at vector-search time:** metadata filters applied during retrieval (no post-retrieval filtering allowed).
* **Operational controls:** rate limiting (rolling hourly window), concurrency limits (stream slots), budget/degraded modes, ingestion atomicity, and blue-green reindex guarantees.
* **Default operational values (recommended):**

  * `RATE_LIMIT_HOURLY = 50` requests per rolling hour (per user) — applies to **originating POST queries** (per REQUIREMENTS.md FR-5.1)
  * `CONCURRENCY_LIMIT = 5` active streams per user — applies to **originating POST query streams**
  * `STREAM_SLOT_TTL = 90` seconds (slot cleanup after abrupt disconnect)
  * `STREAM_TOKEN_TTL = 60` seconds (browser stream-token TTL)
  * `QUERY_RESULT_TTL = 300` seconds (retain completed query results for attach/replay; recommended default 5 minutes)
  * Optional attachment protection defaults (recommended):
    * `ATTACH_CONCURRENCY_LIMIT = 20` (max concurrent GET attachments per user; optional)
    * `ATTACH_RATE_LIMIT_PER_MINUTE = 60` (max GET attaches/min per user; optional)
  * Optional delta buffering defaults (recommended):
    * `MAX_BUFFERED_DELTAS = 200`
    * `MAX_BUFFERED_DELTA_BYTES = 262144` (256KB)
  * Optional long-stream protection (recommended):
    * `MAX_STREAM_DURATION = 120` seconds (maximum allowed end-to-end query stream runtime; deployment-tunable)
  * `MAX_SNIPPET_CHARS = 500` (snippet truncation)
  * `CHUNK_MAX_TOKENS = 512` (per REQUIREMENTS.md FR-3.1 and DECISIONS.md 5.2)
  * `CHUNK_OVERLAP_TOKENS = 50` (approximately 10%; per DECISIONS.md 5.2)
  * `DEFAULT_REFUSAL_THRESHOLD = 0.65`

All these defaults are recommendations; make them configurable per-deployment.

---

# Authentication

All endpoints except `/health`, `/ready`, and `/metrics` require a valid JWT bearer token **or** (for browser streaming) a valid `stream_token` where explicitly allowed.

**Header:**

Authorization: Bearer <jwt_token>

**Minimum required JWT claims (server authoritative):**

* `sub` (string): canonical user id (used for RBAC)
* `role` (string): `admin` | `user`
* `exp` (integer): expiration (Unix epoch seconds)

**Security Notes**

* Server MUST validate `sub` and `exp` and base authorization on server-side identity and policies.
* Client-injected claims (e.g., `allowed_user_ids`) are non-authoritative hints only and MUST NOT be used to grant access.
* On auth failure return `401 Unauthorized`. On valid token but insufficient privileges return `403 Forbidden`.

---

# Common Concepts & Operational Clarifications

## Namespace

* Many operations are scoped to a `namespace` (examples: `dev`, `staging`, `prod`).
* If `namespace` is omitted in `/query`, server MUST resolve it from the authenticated user’s environment (implementation-defined) and MUST NOT default to a privileged namespace.

## Identifiers: `query_id` (required constraints)

* `query_id` is a **public**, opaque identifier for tracing and feedback linkage.
* Format: servers MAY use UUIDs, but clients MUST treat it as an opaque string.
* Constraints (required):

  * max length: 64 characters
  * allowed characters: URL-safe ASCII (`A–Z a–z 0–9 - _`), unless percent-encoded
* `query_id` MUST NOT be guessable if it enables access to any additional data (e.g., logs). Do not embed sequential IDs.

## Transport compatibility: SSE over POST vs browser support (required)

The server **guarantees SSE framing semantics** (SSE event lines, `event:` name, `data:` block containing JSON). Because client environments differ:

**Supported options (recommend supporting both):**

1. **POST SSE (programmatic clients)** — `POST /api/v1/query` returns an SSE-framed response over a streaming HTTP response. Suitable for server-side or native clients that can send POST and read streaming HTTP responses.
2. **GET SSE proxy (browser clients, recommended)** — `GET /api/v1/query/stream?query_id=<id>&token=<stream_token>` streams results for browsers that use `EventSource` (which often only supports GET).

### Required SSE Response Headers (new, required)

For any streaming SSE response (`POST /query` when streaming and `GET /query/stream`), the server MUST set:

* `Content-Type: text/event-stream; charset=utf-8`
* `Cache-Control: no-cache, no-transform`
* `Connection: keep-alive` (where applicable)

Operators SHOULD additionally set:

* `X-Accel-Buffering: no` (for nginx, where supported)

### Browser / Security Guidance (required)

**Short-lived signed token approach (recommended):**

* `POST /api/v1/query` starts the query and streams SSE.
* If the deployment supports token-based `/query/stream`, the server MUST emit a **`meta` SSE event** early in the stream (see “Canonical event names”) containing `query_id` and a short-lived `stream_token` (TTL recommended 60s).
* Browser then calls: `GET /api/v1/query/stream?query_id=<id>&token=<stream_token>`.

**Cookie-based auth (allowed but harder):**
If the GET proxy uses cookie auth, servers MUST implement CSRF protections (e.g., SameSite cookies + CSRF token/double-submit cookie). Do not rely on unauthenticated GET streams.

**CORS:**
When streaming cross-origin, the server MUST set `Access-Control-Allow-Origin` for allowed origins and expose any required headers. Restrict origins tightly. If credentials are used, configure `Access-Control-Allow-Credentials` appropriately.

**Proxy/load-balancer config:**
Operators MUST disable response buffering and set long upstream timeouts (e.g., nginx `proxy_buffering off`, appropriate `proxy_read_timeout`) to avoid truncated/blocked streams. Document exact settings in the ops appendix.

**Query-string token logging (required operator guidance):**
Because `stream_token` is passed in the query string, operators MUST ensure it is not persisted in logs:

* Do not log query strings for `/api/v1/query/stream`, OR
* redact `token` at the proxy/app logging layer.

Failure to do so may leak stream access tokens via logs/analytics.

**Referrer leakage (new, required operator/app guidance):**
Because tokens may appear in URLs, deployments SHOULD set a conservative referrer policy on relevant web properties and/or streaming responses:

* Recommended header: `Referrer-Policy: no-referrer` (strictest), OR
* `Referrer-Policy: strict-origin` (weaker, but safer than default).

Web apps SHOULD avoid navigating to third-party origins while a tokenized stream URL is in the address bar/history.

**Summary:** Provide POST for programmatic clients and a GET SSE proxy for browsers; secure the GET proxy via short-lived tokens or safe cookie patterns and prevent token leakage via logs and referrers.

## Event framing semantics

* Each SSE event uses stable canonical names and a JSON `data` payload encoded in UTF-8.
* The server MUST send only complete valid JSON objects in `data` fields. Do **not** send partial JSON.
* The server MUST not interleave partial multi-byte UTF-8 sequences across frames.

## Canonical event names (must use)

* `meta` — **non-terminal** metadata needed for attaching browser streams. Payload schema:

  * `{ "query_id": "<string>", "stream_token": "<string>", "stream_token_expires_at": "<ISO8601Z>" }`

  Rules:

  * `meta` MUST be emitted **at most once** per query stream.
  * **Ordering (required):** if the server emits `meta`, it MUST be emitted **before the first** `delta` **and before** any terminal `done` event.

    * Rationale: clients relying on GET attach must be able to obtain `query_id` and `stream_token` deterministically.

### Stream-token security model (required)

`stream_token` is used only for GET streaming attachment. To prevent ambiguity and ensure consistent client reconnect behavior:

* `stream_token` MUST be **cryptographically signed** (or otherwise tamper-evident) and MUST be **unguessable**.
* `stream_token` MUST embed (or be server-side bound to) at least: `query_id`, `user_id`, and an expiration time.
* **Replay policy (required default):** reuse within `STREAM_TOKEN_TTL` is permitted (multi-use) unless a deployment explicitly enables single-use tokens.
* **Single-use definition (required if enabled):** single-use means the token authorizes **exactly one successful attachment**. After the first successful attach, the server MUST invalidate the token and subsequent attaches using the same token MUST return `401 Unauthorized` (non-streaming HTTP JSON error).
* Regardless of single-use vs multi-use, tokens MUST be scoped to `(user_id, query_id)` and MUST NOT authorize access to any other query.

### `meta` emission requirement (required)

* If the deployment supports **token-based** GET streaming (`/api/v1/query/stream?token=...`), then `meta` MUST be emitted **exactly once** for every **accepted** `/api/v1/query` request, including refusal and degraded outcomes, and MUST precede any `delta` or terminal `done`.

* If the deployment does **not** support token-based GET streaming (e.g., cookie-only, or GET streaming disabled), servers MAY omit `meta`.

* `delta` — incremental answer text (non-terminal). Payload schema: `{ "content": "<string>" }`.

* `done` — terminal success event; payload is the final aggregated JSON response (see `/query` done schema).

* `error` — terminal failure event; payload follows standard error schema; server MUST close connection after sending `error`.

**Do NOT** use alternate event names (e.g., `token`) in production.

## Streaming notes

* `delta` may be emitted as single characters, words, or multi-character blocks depending on batching. The server SHOULD choose chunk sizes for efficient rendering and network behaviour.
* **Maximum delta guidance (recommended):** servers SHOULD keep each `delta.data.content` under ~8KB to avoid UI and buffering issues.
* `delta` MUST NOT include `sources`, `cost_info`, or secrets. The final `done` event contains sources and cost metadata (except in catastrophic failures where `error` may be used).

## Optional maximum stream duration (recommended)

To prevent unbounded streams under pathological backends or model stalls:

* Deployments SHOULD define and enforce `MAX_STREAM_DURATION`.
* When exceeded, servers MUST terminate deterministically as a stream failure:

  * **Pre-accept**: reject as HTTP `503` with `error_code="STREAM_DURATION_EXCEEDED"`, OR
  * **Post-accept**: send terminal `error` SSE event with `error_code="STREAM_DURATION_EXCEEDED"` and close.

If enforced, document the value and client retry guidance.

---

# Query Outcome Modes (terminal `done.mode`)

Every terminal `done` payload MUST include a `mode` describing why an answer may be missing.

Allowed `mode` values:

* `rag` — answer generated (normal)
* `refusal` — top retrieval similarity < configured threshold; `answer` = null
* `retrieval_only` — client requested retrieval-only; `answer` = null
* `degraded_budget` — budget exceeded; retrieval-only; `answer` = null
* `degraded_llm` — LLM unavailable/failure; retrieval-only; `answer` = null

---

# Confidence vs Threshold (explicit)

Two separate values are used:

* **Threshold (policy)**: numeric cutoff used to *decide whether to refuse*. Configurable per `namespace + index_version`. Default recommended: `0.65` (per REQUIREMENTS.md FR-3.3).
* **Confidence label (UI band)**: derived from the original cosine similarity of the top retrieved chunk (implementation detail; per REQUIREMENTS.md FR-6.3):

  * `high`: cosine ≥ 0.85
  * `medium`: 0.70 ≤ cosine < 0.85
  * `low`: cosine < 0.70

**Important:**

* Refusal uses the *threshold* (e.g., 0.65) and compares against cosine similarity only (per ARCHITECTURE.md Invariant B and E).
* Confidence label uses bands. It is valid that an answer is produced (top score ≥ threshold) yet labeled `low` if score < 0.70.

**UI guidance:** show both the `confidence` label and the numeric `top_score` when `include_debug=true` to avoid confusion.

**Examples (explicit):**

* `top_score = 0.64`, `threshold = 0.65` → `mode="refusal"`, `confidence="low"`, `answer=null`.
* `top_score = 0.65`, `threshold = 0.65` → `mode="rag"`, `confidence="low"` (equality permits generation if policy uses `>=` to permit).
* `top_score = 0.68`, `threshold = 0.65` → `mode="rag"`, `confidence="low"`.
* `top_score = 0.72`, `threshold = 0.65` → `mode="rag"`, `confidence="medium"`.

Operators MUST document whether threshold comparison is `>=` or `>`; default recommended: `>=` (i.e., equal to threshold permits generation).

---

# RBAC Visibility Rule (canonical) & `shared` semantics

**Retrieval filter (applied in vector search metadata per ARCHITECTURE.md Invariant D):**
A chunk is retrievable if:

* `visibility == "public"`, OR
* `allowed_user_ids` contains the authenticated user id (`sub`)

**Visibility semantics (MVP v1):**

* `public`: visible to all users. When `visibility="public"`, `allowed_user_ids` MUST be empty.
* `private`: `allowed_user_ids` contains explicit user IDs only.

**Note on `shared` and group-based RBAC (v2 future feature):**

* `shared` visibility with group IDs (format `group:<id>`) is a planned v2 enhancement not yet specified in backbone documents (ARCHITECTURE.md v1.6, DECISIONS.md v1.5).
* If implementing early, group resolution MUST follow fail-closed behavior:

**Group resolution failure behavior (if implementing groups):**

* If the identity service is unavailable or group membership cannot be resolved, the server MUST **fail closed**:

  * treat group membership as empty (no group-based access granted).
  * continue processing using only `public` and explicit user-id access.

* If fail-closed behavior results in no retrievable chunks, proceed with normal refusal semantics (`mode="refusal"`) unless the failure occurs after stream acceptance and retrieval cannot proceed at all, in which case an `error` event may be used (see Error routing rules).

* **Admin bypass (operator diagnostic mode, production scope clarification):**

  * Admin role MAY have controlled bypass privileges for source visibility diagnostics.
  * **Scope (required clarification):** Admin bypass (e.g., `admin_bypass=true` mode) applies **only to source visibility** for diagnostic purposes (allows admin to retrieve and view sources regardless of `visibility` or `allowed_user_ids` metadata). It does **NOT** bypass RBAC for regular user queries (i.e., admin cannot query on behalf of another user without explicit impersonation controls).
  * Admin bypass MUST be:

    * **Explicit:** controlled via an explicit request parameter or dedicated admin endpoint (not automatic for all admin queries).
    * **Auditable:** all admin bypass queries MUST be logged with `admin_bypass=true` flag and admin user identity.
    * **Diagnostic-only:** intended for troubleshooting metadata/RBAC issues, not for routine querying.
  * Do **not** implement wildcard patterns like `allowed_user_ids=["*"]` in metadata.

**Guarantee:** RBAC must be enforced in the vector search metadata filter to prevent leakage. All sources returned in `done` (including in `refusal` mode) MUST be RBAC-filtered.

---

# Rate Limiting (hourly rolling + concurrency) — behavior & headers

**Limits (per REQUIREMENTS.md FR-5.1 and deployment defaults):**

* Hourly rolling window: `50` requests per rolling 1-hour window (per user).
* Concurrency: `5` concurrent active query streams per user.
* Storage: Redis (sliding window via sorted set or equivalent).

## Concurrency accounting (required clarification)

* The `CONCURRENCY_LIMIT` applies to **originating query streams** (i.e., active `/api/v1/query` POST requests that have been accepted and have an associated stream slot).
* **GET `/api/v1/query/stream` attachments do NOT count** toward `CONCURRENCY_LIMIT` by default (recommended), because they are passive views of an already-running query.
* Deployments MAY optionally enforce a separate limit for attachments (e.g., `ATTACH_CONCURRENCY_LIMIT`) to protect infrastructure; if enabled, document it and return a distinct `error_code` on violation (recommend `ATTACH_LIMIT_EXCEEDED`).

## GET attachment rate limiting (required clarification)

* By default (recommended), GET `/api/v1/query/stream` attachments:

  * MUST NOT increment the hourly `RATE_LIMIT_HOURLY` counter, and
  * MUST NOT reduce `X-RateLimit-Remaining` for originating query calls.
* Deployments SHOULD protect against reconnect storms via one or both of:

  * an attachment concurrency limit (`ATTACH_CONCURRENCY_LIMIT`), and/or
  * an attachment rate limit (e.g., `ATTACH_RATE_LIMIT_PER_MINUTE`), and/or
  * strict `STREAM_TOKEN_TTL` with validation.
* If an attachment limit is violated, servers SHOULD return **HTTP 429** with `error_code="ATTACH_LIMIT_EXCEEDED"` and MAY include `Retry-After`.

**Concurrency exceed behavior (originating streams):**

* If a user attempts a 6th concurrent originating query stream, server MUST reject with **HTTP 429** and `error_code="RATE_LIMIT_CONCURRENCY_EXCEEDED"`.
* The rejected request MUST NOT increment the hourly counter.

**Rate-limit headers (server SHOULD include on initial `/query` response when possible):**

* `X-RateLimit-Limit`: integer (e.g., 50)
* `X-RateLimit-Remaining`: integer
* `X-RateLimit-Reset`: integer (Unix timestamp) — **semantic for rolling windows:** earliest timestamp when enough usage tokens will expire so that one more request will be allowed (i.e., the earliest time when sliding-window count < limit).
* Optional (recommended) concurrency headers:

  * `X-Concurrency-Limit`: integer (e.g., 5)
  * `X-Concurrency-Remaining`: integer

### Rolling-window reset example (required)

Example: If the limit is 50 requests/hour and a user makes 50 requests between `10:00:00` and `10:15:00`, and the earliest request in the window occurred at `10:00:05`, then `X-RateLimit-Reset` SHOULD be the Unix timestamp corresponding to `11:00:05Z` (the moment that earliest request falls out of the rolling window and one additional request becomes allowable).

**Retry behavior (required clarification):**

* `Retry-After` SHOULD be included for `429` and `503`.
* `Retry-After` header value MUST be either:

  * an integer number of seconds until retry is allowed (preferred), OR
  * an HTTP-date (RFC 7231).
* If seconds are used, operators SHOULD ensure the value aligns with `X-RateLimit-Reset` for hourly-limited requests.

**Redis unavailable behavior:** If Redis is down, the system MUST enter a *degraded enforcement mode* (implementation-defined) — do not block all requests solely due to Redis failure. Emit a diagnostic header (e.g., `X-RateLimit-Degraded: true`) and increase observability.

**Concurrency + hourly counter atomicity (operator guidance):**

* Concurrency check and hourly counter increment MUST be performed atomically (single transaction or atomic script) against the rate-limiter store to prevent race conditions.
* Slot acquisition MUST occur only after the atomic operation succeeds; partial failures MUST not consume hourly quota or leak slots.
* On stream close (graceful), decrement the concurrency count immediately. On unexpected disconnect, release the slot after `STREAM_SLOT_TTL` seconds (configurable, recommended default 90s).
* Operators SHOULD emit a metric `concurrency_orphans_total` and an alert if orphaned slots increase.

---

# Standard Error Format (non-streaming) & streamed `error` event

**Non-streaming error JSON schema:**

error_code (STRING), message (human-readable), details (object or null), timestamp (ISO 8601 UTC string), request_id (string)

## Deterministic error routing rules (required)

To make client behavior testable, use the following rule table:

| Failure detected when…                       | Retrieval results available? | Response form                                                                                                   |
| -------------------------------------------- | ---------------------------: | --------------------------------------------------------------------------------------------------------------- |
| **Pre-accept** (before any SSE bytes sent)   |                          n/a | **HTTP error response** (4xx/5xx JSON)                                                                          |
| **Post-accept** (SSE stream already started) |                      **Yes** | **terminal `done`** with a degraded mode when possible (`degraded_llm`, `degraded_budget`, or `retrieval_only`) |
| **Post-accept**                              |     **No** (cannot retrieve) | **terminal `error`** SSE event then close                                                                       |

Additional notes:

* Invalid JWT, invalid body schema, rate-limit reject, and forbidden access MUST be handled **pre-accept** as HTTP errors.
* LLM failure after retrieval MUST return `done` with `mode="degraded_llm"` (not `error`) unless it prevents producing any retrieval output.
* `STREAM_DURATION_EXCEEDED` is treated as a **terminal stream failure** and MUST be emitted as `error` post-accept.

---

# Endpoints (full contract)

## 1) Query API — POST `/api/v1/query` (primary)

**Purpose:** Execute a natural language query against indexed docs using the RAG pipeline.

**Authentication:** Required (user or admin)
**Rate Limit:** Hourly rolling + concurrency (originating streams)
**Response Type:** Streaming SSE

### Request Body (JSON) — summary

* `query` (string, required): natural language question, max **500** chars, must not be empty.
* `namespace` (string, optional): target namespace.
* `retrieval_only` (boolean, optional, default `false`): skip generation and return sources only.
* `include_debug` (boolean, optional, default `false`): include non-sensitive debug metadata (per-stage latencies, top_score, effective threshold). Debug MUST NOT include secrets or raw credentials.

### Request validation & size limits (required)

* **Maximum JSON body size:** 10 KB (servers MUST reject larger payloads with HTTP 413).
* **Maximum query length:** 500 characters (validated; return HTTP 400 `INVALID_QUERY` if exceeded).
* **Maximum feedback comment length:** 500 characters (see Feedback API).

### Idempotency (optional but recommended for production)

* Clients MAY include an `Idempotency-Key` header (format: opaque string, max 128 chars, URL-safe ASCII recommended).
* If provided, server SHOULD deduplicate repeated requests with the same key within a retention window (recommended: 24 hours):

  * On duplicate: return cached `query_id` and result status (do not re-execute query or re-charge user).
  * `cost_info` MUST reflect the original execution (do not double-charge).
* If not implemented, document that retries may double-charge users and clients should avoid retrying completed queries.
* Idempotency keys MUST be scoped per user (keys from different users do not collide).

### Streaming Events (canonical)

* **`meta`** (non-terminal, at most once, REQUIRED ordering): `{ "query_id": "...", "stream_token": "...", "stream_token_expires_at": "..." }`
* **`delta`** (incremental): `{ "content": "<string>" }` — appended text chunks. No sources/costs.
* **`done`** (terminal success) — full aggregated payload (see `done` schema below).
* **`error`** (terminal failure) — standard error JSON payload; connection closed after this.

### `done` payload (fields required / semantics)

* `mode` (string): one of `rag`, `refusal`, `retrieval_only`, `degraded_budget`, `degraded_llm`.
* `answer` (string | null): present **only** when `mode="rag"`.
* `sources` (array of source objects): RBAC-eligible sources. In `refusal`, top up to 3 closest matches (RBAC-filtered). May be empty only if retrieval failed entirely (which usually produces `error`).
* `confidence` (`high` | `medium` | `low`): derived from numeric top chunk cosine score and mapped to bands.
* `refusal_reason` (string | null): MUST be null for `mode="rag"`. For refusal/degraded modes MUST be non-null and include the effective threshold numeric value when applicable.
* `cost_info` (object): `embedding_tokens`, `llm_input_tokens`, `llm_output_tokens`, `total_cost_usd`, `budget_status` (`available` | `warning` | `exceeded`), `utilization` (ratio).

  * **Cost counting rules (required clarification):**

    * In `refusal` mode (low similarity), `llm_input_tokens` and `llm_output_tokens` MUST be **zero** (only embedding cost incurred; no LLM called).
    * In `degraded_budget` mode, `llm_input_tokens` and `llm_output_tokens` MUST be **zero** (retrieval-only; no LLM called).
    * In `degraded_llm` mode, `llm_input_tokens` and `llm_output_tokens` MUST be **zero** (LLM unavailable).
    * In `rag` mode, all token counts reflect actual usage.
* `query_id` (string): public stable id for tracing and feedback linkage (see constraints above).
* `query_log_id` (string | optional): persisted query log id (if exposed; see Query log exposure rules).
* `top_score` (number, optional but recommended): numeric original cosine similarity of top chunk (useful for UI debugging when `include_debug` is true).

**Query log exposure rules (required clarification):**

* `query_id` MUST be returned to all authenticated callers.
* `query_log_id` SHOULD be returned only when **(a)** `include_debug=true` OR **(b)** caller role is `admin`. If exposed to regular users, ensure it does not allow access to other users’ logs and is not guessable.
* Query logs may contain PII; enforce retention and access controls (see Privacy section).

**Source object schema (descriptive):**

* `citation_id` (integer): 1-based ordinal.
* `repo` (string)
* `file_path` (string)
* `start_line` (integer)
* `end_line` (integer)
* `url` (string) — deep-linked when supported.
* `snippet` (string) — server-sanitized and truncated (see Snippet Sanitization).
* `cosine_score` (number) — original similarity score used for confidence.

### Snippet Sanitization (MUST, testable)

* Server MUST truncate `snippet` to `MAX_SNIPPET_CHARS` (recommend 500).
* Server MUST replace redacted content with the literal marker: `[REDACTED]`.
* Server MUST remove or redact lines containing private key material and must never emit PEM blocks.
* Server MUST apply redaction for common secret patterns, including (non-exhaustive):

  * JWT-like tokens (`xxxxx.yyyyy.zzzzz`)
  * AWS access keys (`AKIA...`) and secret-like companions
  * Google API keys (`AIza...`)
  * Slack tokens (`xoxb-`, `xoxp-`)
  * Generic “Bearer ” tokens
  * PEM headers (`-----BEGIN ... PRIVATE KEY-----`)
* Server SHOULD redact obvious PII patterns (emails, phone-like, SSN-like) where practical.
* Debug mode must never disable sanitization.

### Refusal contract (restated)

* Perform retrieval → compute original top chunk cosine `top_score`.
* If `top_score < effective_threshold` (namespace + index_version; default 0.65), DO NOT generate an answer. Return terminal `done` with:

  * `mode="refusal"`, `answer=null`, `confidence="low"`, `refusal_reason` including effective threshold numeric value and rationale, and `sources` containing up to top 3 RBAC-filtered matches.

### Degraded modes

* `degraded_budget`: monthly spend cap exceeded — operate retrieval-only. `cost_info.budget_status="exceeded"`.

  * **Budget check timing (required clarification):** Budget check occurs **before the generation stage**. If budget is exceeded at query-time, the system enters `degraded_budget` mode immediately (retrieval-only). If budget becomes exceeded mid-stream during an active generation (rare edge case), the current response completes normally (do NOT abort mid-response); the **next** query from that user enters `degraded_budget` mode. This prevents breaking in-flight responses.
* `degraded_llm`: retrieval succeeded but LLM failed/unavailable — return retrieval-only response with `mode="degraded_llm"` and explain `refusal_reason`.

### Index safety conflicts (HTTP 409) details

* `EMBEDDING_MODEL_MISMATCH` details MUST include: `expected_model_id`, `received_model_id`, `namespace`, `source_id` (if applicable), `action_required`.
* `INDEX_VERSION_MISMATCH` details MUST include: `expected_index_version`, `received_index_version`, `namespace`, `source_id`, `action_required`.

### Query errors summary (HTTP status)

* `400 INVALID_QUERY` — invalid schema, missing/empty query, or over-length.
* `401 UNAUTHORIZED` — invalid/missing token.
* `403 FORBIDDEN` — insufficient privileges.
* `409 EMBEDDING_MODEL_MISMATCH / INDEX_VERSION_MISMATCH`.
* `429 RATE_LIMIT_EXCEEDED / RATE_LIMIT_CONCURRENCY_EXCEEDED`.
* `503 VECTOR_DB_UNAVAILABLE` — vector store unreachable.

**Rate-limit headers:** server SHOULD include `X-RateLimit-*` and optional `X-Concurrency-*` headers as defined above.

---

## 1b) Browser Streaming Proxy — GET `/api/v1/query/stream` (required if supporting browsers)

**Purpose:** Provide an EventSource-compatible GET endpoint that streams SSE for an already-started query.

**Authentication (required):**
One of the following MUST be used (choose per deployment):

1. **Token-based (recommended):** `token=<stream_token>` query param, scoped to `(user_id, query_id)` and short-lived (`STREAM_TOKEN_TTL`).
2. **Cookie-based:** allowed only if CSRF protections are implemented and documented.

### Query Parameters

* `query_id` (string, required): the query to attach to.
* `token` (string, required for token-based auth): short-lived stream token.

### Query lifetime & retention (required)

* `QUERY_RESULT_TTL` countdown begins at the time the terminal `done` event is generated.

* The system MUST retain the **final terminal `done` payload** for at least `QUERY_RESULT_TTL` seconds after query completion (recommended default 300s).

* Replaying buffered `delta` events is OPTIONAL. If implemented:

  * the server MUST cap buffered deltas by both `MAX_BUFFERED_DELTAS` and `MAX_BUFFERED_DELTA_BYTES` (or equivalent),
  * the server MUST buffer deltas from stream acceptance until caps are reached; once caps are reached, oldest buffered deltas MAY be dropped,
  * the server MUST replay deltas in their original emission order (deterministic and stable ordering),
  * the server MUST still ensure the stream ends with exactly one terminal `done` or `error`.

* After the retention window elapses, the query is considered expired/purged for streaming purposes and MUST return `410 Gone`.

### Attach semantics (required clarification)

Recommended behavior: **replay + live**.

* If the query is **in progress**, server SHOULD:

  * (optionally) replay buffered `delta` events (if buffering enabled), in original emission order up to the configured caps,
  * then stream **future** `delta` events as they occur,
  * and end with the terminal `done` or `error`.
* If the query is **already completed** and still within retention, server SHOULD:

  * replay a minimal stream consisting of a single terminal `done` event (preferred), OR
  * (optionally) replay buffered `delta` events and then a terminal `done`.

Deployments MAY choose “live-only” (no replay) or “no in-progress attach” behaviors, but MUST document it. If in-progress attach is disallowed, return `409 Conflict` with `error_code="STREAM_ATTACH_CONFLICT"`.

### Behavior

* If authentication fails (missing/invalid/expired token or invalid cookie) → `401 Unauthorized` (non-streaming HTTP JSON error).
* If authenticated but not authorized for this `query_id` → `403 Forbidden`.
* If `query_id` does not exist → `404 Not Found`.
* If `query_id` exists but has been fully purged/expired → **`410 Gone` (REQUIRED, preferred over 404)**.

  * Rationale: clients can distinguish “unknown id” from “known but expired”.
* **Multiple attachments:** server MAY allow multiple concurrent attachments to the same `query_id` for the same authorized user. If disallowed, return `409 Conflict` with `error_code="STREAM_ATTACH_CONFLICT"`.

### Streaming events

* The GET proxy MAY emit `meta` (optional; may omit if client already has it).
* If buffered `delta` events are available and replay is enabled, server MAY replay them subject to buffer caps and replay ordering rules above.
* The stream MUST end with exactly one terminal `done` or `error`.

---

## 2) Feedback API — POST `/api/v1/feedback`

**Purpose:** submit feedback tied to a prior query.

**Authentication:** Required (user or admin).

**Linkage rules (required):**

* Request MUST include **exactly one** of:

  * `query_id` (string) — public id from `/query` `done`.
  * `query_log_id` (string) — persisted query log id (if exposed).
* If both or none provided, return `400 INVALID_FEEDBACK_LINKAGE`.

**Authorization (required clarification):**

* For non-admin users: linkage MUST refer to a query owned by the authenticated user (`sub`).
* Admin callers MAY submit feedback for any query only if explicitly enabled by operator policy; such actions MUST be auditable.

**Request fields:**

* `query_id` OR `query_log_id` (see above)
* `feedback` (integer): `1` (thumbs up) or `-1` (thumbs down)
* `comment` (string, optional): max 500 chars

**Success (200):**

* `status: "stored"`
* `query_id` or `query_log_id` echoed
* `stored_at` (ISO 8601 UTC timestamp)

**Server behavior (required per REQUIREMENTS.md FR-5.3, idempotent-by-default):**

* Server MUST deduplicate feedback per `(user_id, linkage_id)` by **replacing** prior feedback from the same user for the same linkage id (idempotent-by-default).
* If deployments choose to allow multiple feedback records, they MUST:

  * explicitly document the behavior, and
  * provide an idempotency strategy (e.g., idempotency key) to prevent accidental duplicates.
* Rate-limit feedback submissions to prevent abuse.
* Validate linkage id existence; if not, return `404 Not Found`.

---

## 3) Ingestion API — POST `/api/v1/ingest` and status endpoints

**Purpose:** trigger ingestion from connectors (currently `github`).

**Authentication:** Admin-only. Rate limit: none (recommend operator controls).

**Request fields:**

* `source_type` (string) — `github` supported
* `repo_url` (string) — valid GitHub repo URL
* `branch` (string; default `main`)
* `file_patterns` (array of strings; default `["**/*.md"]`)
* `exclude_patterns` (array)
* `visibility` (`public` | `private`; default `private`) — Note: `shared` with group IDs is a v2 feature not yet in backbone docs
* `allowed_user_ids` (array; required for `private`)
* `namespace` (string; required)

**Credential safety (new, required):**

* `repo_url` MUST NOT include embedded credentials (tokens, username:password, etc.).
* Connector authentication MUST be provided via server-managed secrets (implementation-defined).

**Visibility validation (per DECISIONS.md 5.1):**

* `public` → server MUST ensure `allowed_user_ids` empty.
* `private` → `allowed_user_ids` must be non-empty.

**Atomicity guarantee (per ARCHITECTURE.md Invariant A - Index Lifecycle Contract):**

* Source metadata (`last_indexed_sha`, `index_model_id`, `index_version`, namespace selector) MUST be updated atomically **only** after:

  * ingestion pipeline completes,
  * vector upsert succeeds,
  * DB chunk metadata writes succeed,
  * validation checks pass.
* If any step fails, source metadata MUST remain unchanged.

**Behavior on changing existing source visibility / allowed_user_ids:**

* If ingestion modifies visibility or `allowed_user_ids`, server MUST revalidate access model and either:

  * Require operator approval for expanding visibility (e.g., `private` → `public`), OR
  * Automatically apply changes only after successful revalidation per policy.
* Operators MUST document approval flow in the runbook.

**Success response (recommended HTTP 202):**

* `status: "queued"`, `ingest_run_id`, `source_id`, `message`.

**Status endpoint:** GET `/api/v1/ingest/{ingest_run_id}/status` — returns:

* `ingest_run_id`, `status` (`queued`|`running`|`finalizing`|`completed`|`failed`), `progress` (`total_files`, `processed_files`, `total_chunks`, `indexed_chunks`), `started_at`, `estimated_completion`, `error` (safe).

**Delete source:** DELETE `/api/v1/sources/{source_id}` — admin-only: remove source and associated vectors/metadata; return `deleted_chunks` and `status`.

---

## 4) Admin API — sources, reindex, thresholds

### GET `/api/v1/admin/sources`

* **Authentication:** Admin-only.
* **Pagination & filters (required):**

  * Query params: `?page=<int>&per_page=<int>&namespace=<string>&visibility=<public|private>`
  * Default `per_page` recommended 50; server MUST enforce `max_per_page` to avoid huge responses.
* **Response (required fields):**

  * `page` (int)
  * `per_page` (int)
  * `total` (int) — total sources matching filters
  * `has_more` (boolean)
  * `sources` (array) with each entry:

    * `source_id`, `repo`, `source_type`, `namespace`,
    * `index_metadata` (`index_model_id`, `index_version`, `last_indexed_sha`, `last_indexed_at`),
    * `chunk_count`, `visibility`, `allowed_user_ids`.

### POST `/api/v1/admin/reindex`

* **Request:** `source_id` (string), `new_index_version` (int), `validation_query_count` (int, default 10).
* **Guarantees:** Blue-green reindex: old index stays active until validation success; swap only after validation; on failure no swap occurs.
* **Response:** `status: "queued"`, `reindex_job_id`, `message`.

### PUT `/api/v1/admin/thresholds`

* **Request:** `namespace`, `index_version`, `threshold` (number, validated, recommended range 0.50–0.90).
* **Response:** `old_threshold`, `new_threshold`, `status: "updated"`.

**Operator guidance:** include runbook for rollback and handling `EMBEDDING_MODEL_MISMATCH` / `INDEX_VERSION_MISMATCH`.

---

## 5) Health, Readiness, Metrics

### GET `/api/v1/health`

* **Auth:** Not required.
* **Timeout:** 5s.
* **Return:** `status` (`healthy` | `degraded`), `timestamp`, `checks` for Postgres, Redis, vector DB, Celery workers. `last_heartbeat` timestamps MUST be ISO 8601 UTC.

### GET `/api/v1/ready`

* **Auth:** Not required.
* **Timeout:** 10s.
* Returns 200 only if required dependencies are healthy (vector DB + worker heartbeat included). LLM check may be optional per deploy.

### GET `/api/v1/metrics`

* **Auth:** Not required for internal scraping (but protect endpoint in public deployments).

* **Format:** Prometheus text format.

* **Minimum metrics & labels (cardinality guidance):**

  * `query_requests_total{namespace, outcome}` counter where `outcome` ∈ {success, refusal, error, degraded_budget, degraded_llm}
  * `query_latency_seconds` histogram (label `namespace`)
  * `embedding_cache_hit_rate{namespace}` gauge
  * `monthly_cost_usd{namespace}` gauge
  * Counters: `refusal_count`, `degraded_budget_count`, `degraded_llm_count`

* **Attachment/streaming metrics (recommended):**

  * `attach_requests_total{namespace}` counter
  * `attach_limit_exceeded_total{namespace}` counter
  * `stream_replay_events_total{namespace}` counter (count of replayed `delta` events sent across attachments)

* **Labeling guidance:** include `namespace` and `env`. **Do NOT** include per-user labels (for cardinality). `index_version` only when cardinality is controlled.

---

# Error Codes Catalog (finalized)

* `400` `INVALID_QUERY` — payload/schema invalid.
* `400` `INVALID_FEEDBACK_LINKAGE` — both or none of `query_id`/`query_log_id`.
* `401` `UNAUTHORIZED`
* `403` `FORBIDDEN`
* `404` `NOT_FOUND` — generic not found (used where applicable)
* `409` `EMBEDDING_MODEL_MISMATCH`
* `409` `INDEX_VERSION_MISMATCH`
* `409` `STREAM_ATTACH_CONFLICT` — attach not allowed / already attached
* `410` `GONE` — query expired/purged (REQUIRED for `/query/stream` expiry)
* `429` `RATE_LIMIT_EXCEEDED`
* `429` `RATE_LIMIT_CONCURRENCY_EXCEEDED`
* `429` `ATTACH_LIMIT_EXCEEDED` — optional (attachment limits/rate limits)
* `503` `VECTOR_DB_UNAVAILABLE`
* `503` `STREAM_DURATION_EXCEEDED` — stream exceeded configured `MAX_STREAM_DURATION` (optional; only if enforced)

For `429` / `503`, server SHOULD include `Retry-After` guidance where applicable.

---

# Snippet Sanitization & Privacy (MUST)

* Server MUST sanitize snippets: redact secrets (API keys, tokens), PII-like patterns, and **must never emit private key material**.
* Server MUST truncate snippets to `MAX_SNIPPET_CHARS` (recommend 500).
* Redactions MUST use `[REDACTED]`.
* Debug mode must never disable sanitization.
* Query logs (`query_log_id` data) may contain PII. Define a retention policy and access controls:

  * **Retention:** default 90 days (operator-configurable).
  * **Access:** restrict to roles with audit logging.
  * **Redaction:** when exposing logs to non-privileged UIs, redact PII.

---

# Query Log / Feedback Retention & Access

* `query_log_id` is a stable persisted identifier for operator troubleshooting. If exposed to clients, ensure retention and access policies are documented and enforced.
* Feedback storage and linkage must honor privacy rules and allow consumers to request deletion if legal requirements demand.

---

# Tests & Validation (required CI)

Add/extend tests to verify:

1. SSE transport integration over POST + GET SSE proxy (with proxies/gateways in path).
2. SSE response headers tests (`Content-Type`, `Cache-Control`, `Connection`) for streaming endpoints.
3. Event naming & payload schema tests (`meta`, `delta`, `done`, `error`) including `meta` ordering (must precede first `delta` and any `done`).
4. `meta` emission tests: if token-based `/query/stream` is enabled, accepted `/query` MUST emit exactly one `meta` event even on refusal/degraded outcomes.
5. Stream-token security tests:

   * token is unguessable/tamper-evident (signature or equivalent),
   * token binds to `(user_id, query_id, exp)`,
   * if single-use is enabled, second attach MUST return 401.
6. Concurrency atomicity + sliding-window tests (simulate abrupt disconnects; ensure 6th originating stream rejected with no counter increment).
7. GET attachment limits/rate tests (if enabled): attach requests MUST NOT consume hourly quota; enforce `ATTACH_*` with `429 ATTACH_LIMIT_EXCEEDED`.
8. RBAC fuzz tests (`public`/`private`/`shared`) to prevent leakage, including group resolution fail-closed.
9. Threshold boundary tests (score == threshold and band boundaries).
10. Rate-limit header tests (rolling-window semantics) and optional concurrency headers if implemented; include a rolling reset example test.
11. Ingestion atomicity tests (mid-pipeline failure => metadata unchanged).
12. Feedback idempotency tests (same user MUST replace previous feedback).
13. Snippet redaction tests (JWT/AWS/PEM patterns redacted; `[REDACTED]` marker; max length enforced).
14. `/query/stream` attach tests: invalid token, expired token, wrong user, completed query replay, expired query MUST return 410; in-progress attach semantics match deployment mode (recommended replay+live); replay order deterministic.
15. If `MAX_STREAM_DURATION` is enforced: ensure `STREAM_DURATION_EXCEEDED` is returned pre-accept as HTTP 503 or post-accept as terminal SSE `error`.

---

# Operational notes & runbook pointers

* **SSE proxying:** document nginx/ALB settings required (disable buffering, long timeouts). Provide example config in operator runbook.
* **SSE headers:** ensure `Content-Type: text/event-stream` and `Cache-Control: no-transform` are preserved by gateways; disable proxy buffering.
* **Stream-token leakage prevention:** ensure `/query/stream` query strings are not logged; redact `token` everywhere (proxy/app/analytics); set a conservative `Referrer-Policy`.
* **Rate-limiter design:** implement atomic check-and-increment (Redis Lua or similar). Use TTL-based cleanup for concurrency slots.
* **Attachment storm controls:** if browsers reconnect frequently, enable `ATTACH_RATE_LIMIT_PER_MINUTE` and/or `ATTACH_CONCURRENCY_LIMIT`.
* **Replay buffering sizing:** if delta replay is enabled, size buffers using `MAX_BUFFERED_DELTAS` and `MAX_BUFFERED_DELTA_BYTES` and monitor `stream_replay_events_total`.
* **Index-safety 409 runbook:** include blue-green reindex steps, validation queries, and rollback commands.
* **Metrics/alerts:** alert on high `refusal_count`, `concurrency_orphans_total`, sudden spikes in `monthly_cost_usd`, and attachment-limit violations if enabled.
* **Timestamps:** all timestamps must be in UTC (ISO 8601 with `Z`).

---

# Appendix — Example `done` payloads (for client teams)

**1) `rag` example**

mode: "rag", answer: "To configure horizontal pod autoscaling, ...", sources array with citation_id, repo, file_path, start_line, end_line, url, snippet, cosine_score; confidence: "high", refusal_reason: null, cost_info with embedding_tokens, llm_input_tokens, llm_output_tokens, total_cost_usd, budget_status, utilization; top_score, query_id, query_log_id

**2) `refusal` example**

mode: "refusal", answer: null, sources array with partial matches (RBAC-filtered), confidence: "low", refusal_reason: "No sources found with sufficient confidence (top_score=0.48, threshold=0.65).", cost_info shows minimal embedding cost only, top_score, query_id

**3) `degraded_budget` example**

mode: "degraded_budget", answer: null, sources array with retrieval results, confidence: "medium", refusal_reason: "Monthly budget exceeded; operating in retrieval-only mode.", cost_info.budget_status: "exceeded", utilization: 1.02, query_id

**4) `degraded_llm` example**

mode: "degraded_llm", answer: null, sources array with retrieval results, confidence: "medium", refusal_reason: "LLM unavailable; showing retrieval-only results.", cost_info.budget_status: "available", query_id

---

# Related Documents

* Architecture (ARCHITECTURE.md) — system architecture and component design
* Requirements (REQUIREMENTS.md) — functional & non-functional requirements
* Tech Stack (TECH_STACK.md) — technology choices & tradeoffs
* Decisions (DECISIONS.md) — ADRs
* Operator runbook & SRE playbooks (internal ops folder) — **MUST** include proxy config, Redis atomic scripts guidance, concurrency TTL cleanup, attachment limits (if enabled), blue-green reindex steps, index-safety runbook, and stream-token log-redaction guidance.


