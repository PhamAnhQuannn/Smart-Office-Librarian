# 🧪 TESTING — Smart Office Librarian

**Version:** v1.9.0  
**Status:** Testing Specification (Complete, Standalone, Implementation-Ready)  
**Last Updated:** 2026-03-12  
**Canonical References:** DECISIONS v1.5, REQUIREMENTS v1.5, OPERATIONS v1.3  
**Architecture Target:** v1.5 (Production) + v1.6 (Planned / Optional)

> This document defines **all required tests** for the Smart Office Librarian RAG system. It is **standalone** and includes explicit contracts for SSE, API schemas, metrics naming, environment strategy, and release gates.

---

## 0) Version Alignment & Governance

### 0.1 Canonical Decision Priority

If this testing spec conflicts with:

1. **DECISIONS.md** (wins)
2. **REQUIREMENTS.md**
3. **OPERATIONS.md**
4. This **TESTING.md**

### 0.2 Architecture Version Policy

* **Production baseline:** **Architecture v1.5** (aligned to DECISIONS/REQUIREMENTS/OPERATIONS).
* **Architecture v1.6 items are optional** unless explicitly marked **[V1.6 OPTIONAL]** in this document.

### 0.3 Known Reconciliation: Deduplication

* **v1 canonical behavior:** **SimHash dedupe happens during ingestion only.** No runtime retrieval/generation dedupe is required.
* **REQUIREMENTS FR-3.5** (“Context Deduplication”) is treated as **v2 / optional** unless the implementation explicitly adds runtime dedupe.
* Therefore:
  * **GenerationStage must NOT run SimHash dedupe at runtime.**
  * **Retrieval-time dedupe tests are required only if runtime dedupe is implemented** (flagged optional).

---

## 1) Testing Principles

* **Coverage Target:** >80% code coverage
* **Frameworks:** pytest (backend), Jest + React Testing Library (frontend)
* **Test Data:** Golden Question set (50–100 questions with ground truth)
* **Mocking Rule:** Unit tests use mocks (no external API calls)

---

## 2) System Surface Assumptions

### 2.1 API Endpoints (Required vs Optional)

**Required (v1.5):**

* `POST /api/v1/query` (SSE stream; answer + refusal + retrieval-only all stream)
* `POST /api/v1/ingest` (admin)
* `POST /api/v1/feedback`
* `GET /api/v1/health`
* `GET /metrics` (canonical)

**Optional / Proxy:**

* `GET /api/v1/metrics` (proxy to `/metrics`)
* `GET /api/v1/ready` (**only required if readiness is implemented as an endpoint**; otherwise readiness is tested via internal HealthService gates)

### 2.2 Required Error Contract Classes

* **Index safety mismatches:** HTTP 409 with `error_code` (`EMBEDDING_MODEL_MISMATCH` | `INDEX_VERSION_MISMATCH`) + details fields: `expected_model_id`, `expected_index_version`, `received_model_id`, `received_index_version`
* **Refusal contract:** HTTP 200 via SSE + `mode="refusal"` + `refusal_reason="LOW_SIMILARITY"` + `sources[]`

### 2.3 Non-Streaming Error Rule

* Any request that fails at the API boundary (400/401/403/409/429) returns **non-SSE JSON** using the canonical error schema.
* Only HTTP 200 responses use SSE streaming.

---

## 3) Canonical API Response Schemas

### 3.1 Standard Error JSON Schema (Non-SSE)

Used for 400/401/403/409/429/500 when the stream is not opened:

```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "human readable",
  "request_id": "uuid",
  "details": { "optional": "structured details" }
}
```

**Error code expectations (non-exhaustive, testable):**

* `RATE_LIMIT_EXCEEDED` (429)
* `RATE_LIMIT_CONCURRENCY_EXCEEDED` (429)
* `UNAUTHENTICATED` (401)
* `FORBIDDEN` (403)
* `VALIDATION_ERROR` (400)
* `EMBEDDING_MODEL_MISMATCH` (409)
* `INDEX_VERSION_MISMATCH` (409)
* `INTERNAL_ERROR` (500)

**409 Index safety mismatch schema requirement (details are REQUIRED):**

```json
{
  "error_code": "EMBEDDING_MODEL_MISMATCH",
  "message": "Index safety mismatch",
  "request_id": "uuid",
  "details": {
    "expected_model_id": "text-embedding-3-small-v1",
    "expected_index_version": 1,
    "received_model_id": "text-embedding-3-small-v2",
    "received_index_version": 2
  }
}
```

### 3.2 SSE Stream Contract (Authoritative Answer Policy)

**Authoritative answer text is assembled from `token` events.**
The `complete` event MUST NOT repeat the full answer text. It contains final metadata + citations only.

### 3.3 SSE Message Framing Rules (Deterministic + Standard-Compliant)

* The system uses **data-only SSE** (no `event:` lines required).
* Each SSE message is a JSON payload emitted as one or more SSE `data:` lines and terminated by a blank line:

  * `data: <chunk>\n`
  * `data: <chunk>\n`
  * `\n`
* **Client MUST concatenate all `data:` lines for a single SSE message with `\n`** (SSE standard), then parse as JSON.
* Server SHOULD emit single-line JSON when possible, but **multi-line `data:` messages are allowed**.
* Multi-line splitting is **transport-level only**: after concatenation, the payload MUST be a single valid JSON text.
* Clients MUST ignore SSE comment lines beginning with `:` and any non-`data:` lines.

### 3.4 JSON Encoding Rules

* SSE `data:` payload must be **UTF-8**.
* Each SSE message payload MUST parse as **valid JSON** with **no trailing bytes** after concatenation.
* `token.text` MUST be a JSON string; it may be empty and may contain newlines **only as JSON-escaped sequences** (e.g., `\\n`).

### 3.5 Required SSE Events

Each SSE JSON payload MUST include a `type` field:

1. `start` (first)
2. `token` (0+; **answer mode only**)
3. `complete` (last)
4. `error` (optional; if emitted, stream terminates immediately after)

#### start payload

```json
{
  "type": "start",
  "query_log_id": "uuid",
  "mode": "answer" | "refusal" | "retrieval_only",
  "model_id": "gpt-4o-mini",
  "index_version": 5,
  "namespace": "dev"
}
```

#### token payload

```json
{ "type": "token", "text": "partial output" }
```

**Token concatenation rule:**
Client MUST build the final answer by **exactly concatenating** `token.text` in order, with **no added separators or normalization**.

> Note: In `mode="answer"`, emitting **zero** `token` events is permitted **only if** the intended answer is the empty string. This behavior must be deterministic and tested.

#### complete payload (answer mode)

```json
{
  "type": "complete",
  "query_log_id": "uuid",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "refusal_reason": null,
  "sources": [
    {
      "file_path": "docs/README.md",
      "source_url": "https://...",
      "start_line": 10,
      "end_line": 22,
      "text": "snippet used"
    }
  ]
}
```

#### complete payload (refusal / retrieval-only)

```json
{
  "type": "complete",
  "query_log_id": "uuid",
  "confidence": "LOW",
  "refusal_reason": "LOW_SIMILARITY" | "BUDGET_EXCEEDED" | "LLM_UNAVAILABLE",
  "sources": [ /* same schema */ ]
}
```

#### error payload (SSE)

```json
{
  "type": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "safe message",
  "request_id": "uuid"
}
```

### 3.6 Mode ↔ Reason Rules

* `mode="answer"` ⇒ `refusal_reason MUST be null`
* `mode="refusal"` ⇒ `refusal_reason MUST be "LOW_SIMILARITY"`
* `mode="retrieval_only"` ⇒ `refusal_reason MUST be "BUDGET_EXCEEDED" OR "LLM_UNAVAILABLE"`

### 3.7 Answer-Mode Empty Output Guard (Fix)

* If `mode="answer"` and the assembled answer is the empty string (i.e., zero tokens), `confidence` MUST NOT be `HIGH`.

  * Allowed values: `LOW` or `MEDIUM` (implementation choice, but must be deterministic and tested).

### 3.8 Refusal Streaming Policy (Deterministic)

* In `mode="refusal"`, the server MUST emit **no `token` events**.
* Refusal responses consist of `start` followed by `complete` with `refusal_reason="LOW_SIMILARITY"` and `sources[]`.

### 3.9 Retrieval-Only Streaming Policy (Deterministic)

* In `mode="retrieval_only"`, the server MUST emit **no `token` events**.
* Retrieval-only responses consist of `start` followed by `complete` with:

  * `refusal_reason="BUDGET_EXCEEDED"` **or** `refusal_reason="LLM_UNAVAILABLE"`
  * `sources[]`

### 3.10 Stream Error Handling Policy (Deterministic)

* If the SSE stream has already emitted a `start` event, any unhandled exception MUST emit **exactly one** `error` event and then terminate the stream.
* If the SSE stream has not started (no headers/event sent), errors MUST return non-SSE JSON (standard error schema).

### 3.11 Source Schema Requirements

* `start_line` and `end_line` are required and **1-indexed**.
* `text` is a snippet preview, truncated to **max 500 chars**.
* `source_url` MUST be present:

  * if resolvable URL exists ⇒ string
  * else ⇒ `null` (not omitted)

---

## 4) SSE Transport Requirements

### 4.1 Required SSE Headers

* `Content-Type: text/event-stream`
* `Cache-Control: no-cache`
* `Connection: keep-alive`

### 4.2 Ordering Rules

* First event MUST be `start`
* Last event MUST be `complete` (unless `error`, then terminate immediately after `error`)
* `token` events MUST occur only between `start` and `complete`

### 4.3 Heartbeats (Optional)

If heartbeats are implemented:

* Payload: `{ "type":"heartbeat" }`
* Not counted as tokens
* Frequency ≤ 1 per 15s

### 4.4 Client Disconnect Behavior

* Server MUST release resources and decrement `librarian_active_sse_streams` when a client disconnects.
* If client disconnects mid-stream, server is not required to emit additional events.

### 4.5 Disconnect Observability (Optional)

If implemented, expose:

* Counter: `librarian_sse_disconnects_total`

This metric MUST NOT include high-cardinality labels.

---

## 5) Canonical Metrics Naming (Prometheus)

`GET /metrics` must expose at minimum:

### 5.1 Counters

* `librarian_queries_total{mode="answer|refusal|retrieval_only"}`
* `librarian_refusals_total{reason="LOW_SIMILARITY|BUDGET_EXCEEDED|LLM_UNAVAILABLE"}`
* `librarian_errors_total{code="HTTP_4XX|HTTP_5XX|INTERNAL"}`

### 5.2 Histograms (Prometheus family correctness)

For each histogram prefix below, Prometheus MUST expose:

* `<name>_bucket` (with `le` label)
* `<name>_sum`
* `<name>_count`

Required histogram prefixes:

* `librarian_stage_latency_ms` with label `{stage="embed|vector|rerank|llm|total"}`
* `librarian_ttft_ms` (no additional labels required)

**Label consistency rule:**
For a given histogram prefix, `_sum` and `_count` MUST expose the same labels as the `_bucket` series (minus `le`).

### 5.3 Gauges

* `librarian_active_sse_streams`

### 5.4 Metrics Cardinality Rules

* Metric labels MUST come from **bounded enumerations** (like `mode`, `stage`, `code`, `reason`).
* Metrics MUST NOT include labels derived from user input or high-cardinality identifiers (e.g., `user_id`, `query_text`, `repo`, `file_path`, `namespace`, `query_log_id`).

---

## 6) Architectural Invariants Under Test (v1.5 + Optional v1.6)

### 6.1 Invariants (v1.5 REQUIRED)

* RBAC visibility rule: `visibility == "public"` OR `allowed_user_ids $in [user.id]`
* Source metadata atomicity: update only after successful ingestion/reindex validation
* Default visibility = private
* Threshold compare uses `>=` (equal passes)
* Confidence/refusal uses **cosine** score only
* `/metrics` canonical; `/api/v1/metrics` optional proxy

### 6.2 Invariants (v1.6 OPTIONAL unless promoted)

* No DB imports in RAG layer (purity via injection)
* Threshold fetched by Domain and injected into RAGPipeline
* Celery heartbeat freshness in Redis
* Ingest run atomicity via `ingest_run_id`

---

## 7) Mocking & Environment Strategy

### 7.1 Test Tier Dependency Rules

**Unit**

* Everything mocked (OpenAI, Pinecone, Redis, Postgres, GitHub)

**Integration (CI-safe)**

* Real: Postgres + Redis via Docker
* Mocked: OpenAI + Pinecone + GitHub

**Evaluation**

* CI: mocked OpenAI + Pinecone
* Staging (manual): optionally real OpenAI + Pinecone with budget caps

### 7.2 Integration Test Infra Rules

* Dependencies started via `docker-compose` (or pytest containers)
* Deterministic DB reset:

  * Preferred: transaction rollback per test
  * Alternative: truncate all tables between tests
* Parallel execution:

  * If using xdist, each worker uses isolated DB/schema

### 7.3 Cache Defaults

Unless overridden by environment config:

* Embedding cache TTL default: **24h**
* Retrieval cache TTL default: **60s** (DECISIONS canonical; RBAC scoped)

---

## 8) Release Gates (Explicit Targets)

### 8.1 Dev Gate (local)

* Unit tests: PASS
* Integration tests: optional but recommended

### 8.2 Staging Gate

* Unit + Integration: PASS
* Golden Questions:

  * Refusals counted as **abstention** (excluded from TP/FP/FN counts)
  * Precision ≥ 0.75 (excluding refusals)
  * Recall ≥ 0.75 (excluding refusals)
  * F1 ≥ 0.80 (excluding refusals)
  * Refusal rate ≤ 35%
* Latency:

  * p95 end-to-end ≤ 2.0s

### 8.3 Production Gate

* Unit + Integration + Evaluation: PASS
* Golden Questions:

  * Refusals counted as **abstention** (excluded from TP/FP/FN counts)
  * Precision ≥ 0.80 (excluding refusals)
  * Recall ≥ 0.80 (excluding refusals)
  * F1 ≥ 0.85 (excluding refusals)
  * Refusal rate ≤ 25%
* Latency:

  * p95 end-to-end ≤ 2.0s
  * p99 end-to-end ≤ 3.0s
* Audit logging + retention tests must pass when those features are enabled in production config.
* Flake rule: failing tests must reproduce on re-run; flaky tests are blocked from production.

---

# 9) Unit Tests (Backend)

## 9.1 API Layer Tests

### QueryController Tests (`tests/unit/api/test_query_routes.py`)

* [ ] Valid query returns 200 with SSE stream
* [ ] SSE headers correct
* [ ] SSE framing correct (supports multi-line `data:` messages; JSON parses after concatenation)
* [ ] SSE parsing ignores comment lines beginning with `:` and other non-`data:` lines safely
* [ ] Event ordering: first `start`, last `complete`
* [ ] `start` schema matches canonical
* [ ] `mode="answer"`:

  * [ ] emits `token` events OR emits zero tokens only when answer is empty string (deterministic)
  * [ ] if zero tokens emitted, `confidence MUST NOT be HIGH` (must be deterministic)
  * [ ] token concatenation rule enforced by client (exact concatenation)
  * [ ] `complete` does NOT repeat full answer text (metadata + sources only)
* [ ] `complete` includes `query_log_id` and matches canonical schema for mode
* [ ] Mode ↔ reason rules enforced (`answer => null`, `refusal => LOW_SIMILARITY`, `retrieval_only => BUDGET_EXCEEDED|LLM_UNAVAILABLE`)
* [ ] Invalid request returns 400 JSON error schema
* [ ] Unauthenticated returns 401 JSON error schema
* [ ] Forbidden returns 403 JSON error schema
* [ ] Rate limit returns 429 JSON error schema
* [ ] Index mismatch returns 409 JSON error schema with canonical `error_code` (`EMBEDDING_MODEL_MISMATCH` or `INDEX_VERSION_MISMATCH`) and details fields (`expected_model_id`, `expected_index_version`, `received_model_id`, `received_index_version`)
* [ ] Refusal: `mode="refusal"` emits **no token events**, complete includes LOW_SIMILARITY + sources
* [ ] Retrieval-only: `mode="retrieval_only"` emits **no token events**, complete includes BUDGET_EXCEEDED or LLM_UNAVAILABLE + sources
* [ ] Sources schema:

  * [ ] `source_url` present and nullable (never omitted)
  * [ ] `text` truncated ≤500 chars
  * [ ] `start_line/end_line` are 1-indexed integers
* [ ] Exception after `start` emits single SSE `error` then terminates
* [ ] Exception before stream opens returns 500 JSON error schema
* [ ] Client disconnect mid-stream closes server resources and decrements active stream gauge

### IngestController Tests (`tests/unit/api/test_ingest_routes.py`)

* [ ] Admin ingest returns job_id
* [ ] Non-admin returns 403
* [ ] Invalid URL returns 400
* [ ] Exceptions return 500 JSON error schema

### MetricsController Tests (`tests/unit/api/test_metrics_routes.py`)

* [ ] `GET /metrics` returns Prometheus format
* [ ] Required metric names exist
* [ ] Histogram families expose `_bucket/_sum/_count`
* [ ] Histogram `_bucket` series include `le` label
* [ ] Histogram label sets consistent across bucket/sum/count (bucket has `le`)
* [ ] No high-cardinality labels exist
* [ ] `/api/v1/metrics` proxies if implemented
* [ ] No auth required

### FeedbackController Tests (`tests/unit/api/test_feedback_routes.py`)

* [ ] feedback=1 succeeds
* [ ] feedback=-1 succeeds
* [ ] linked to query_log_id
* [ ] unauth returns 401
* [ ] invalid query_log_id returns 404

### AdminRoutes Tests (`tests/unit/api/test_admin_routes.py`)

* [ ] Non-admin 403; unauth 401
* [ ] sources list paginated
* [ ] create source returns created
* [ ] delete source triggers purge job
* [ ] get thresholds returns current threshold
* [ ] update threshold validates range + logs audit entry
* [ ] get users returns user list
* [ ] exceptions return 500 JSON error schema

### AuthDependency Tests (`tests/unit/api/test_auth_dependency.py`)

* [ ] Valid JWT extracts claims
* [ ] Expired/invalid/missing token returns 401
* [ ] user not found returns 401

### RateLimiterMiddleware Tests (`tests/unit/api/test_rate_limiter.py`)

* [ ] First 50/hour succeed
* [ ] 51st returns 429 RATE_LIMIT_EXCEEDED
* [ ] rolling reset after 1 hour
* [ ] user isolation works
* [ ] Redis down = fail-open
* [ ] 5 concurrent streams ok; 6th returns 429 RATE_LIMIT_CONCURRENCY_EXCEEDED

---

## 9.2 Domain Layer Tests

### ThresholdService (`tests/unit/domain/test_threshold_service.py`) **[REQUIRED]**

* [ ] Get returns stored
* [ ] Default 0.65 if unset
* [ ] Scoped namespace+index_version
* [ ] Update persists + audit log
* [ ] Env isolation

### QueryService (`tests/unit/domain/test_query_service.py`)

* [ ] Answer path
* [ ] Index safety mismatch 409 with canonical code (`EMBEDDING_MODEL_MISMATCH` or `INDEX_VERSION_MISMATCH`)
* [ ] Budget exceeded => retrieval_only
* [ ] Threshold injected into RAGPipeline
* [ ] Refusal path => sources
* [ ] QueryLog fields correct
* [ ] RBAC filter applied
* [ ] Exceptions => 500

### IndexSafetyService (`tests/unit/domain/test_index_safety_service.py`)

* [ ] matches ok
* [ ] mismatches => 409 codes
* [ ] missing Source error
* [ ] missing selector config error

### IngestService (`tests/unit/domain/test_ingest_service.py`)

* [ ] queues job
* [ ] >1MB reject
* [ ] >200 chunks reject
* [ ] atomic Source metadata update only after success
* [ ] incremental sync
* [ ] default visibility private

### RBACService (`tests/unit/domain/test_rbac_service.py`)

* [ ] OR filter logic
* [ ] public retrievable
* [ ] private requires allowed list
* [ ] shared requires allowed list **[V2 OPTIONAL]**
* [ ] admin wildcard
* [ ] Pinecone filter syntax

### EvaluationService (`tests/unit/domain/test_evaluation_service.py`)

* [ ] loads dataset
* [ ] P/R/F1 correct
* [ ] optimal threshold
* [ ] failure taxonomy + aggregation
* [ ] longitudinal persistence

### FeedbackService (`tests/unit/domain/test_feedback_service.py`)

* [ ] stored correctly
* [ ] duplicates handled
* [ ] downvote flagged
* [ ] does not mutate QueryLog

### CostService (`tests/unit/domain/test_cost_service.py`)

* [ ] spend calc correct
* [ ] budget state correct
* [ ] retrieval-only on exceeded
* [ ] monthly reset

### HealthService (`tests/unit/domain/test_health_service.py`)

* [ ] Postgres/Redis/Pinecone checks + timeouts
* [ ] LLM optional
* [ ] /health core deps
* [ ] /ready optional if implemented

---

## 9.3 RAG Pipeline Tests

### RAGPipeline (`tests/unit/rag/test_pipeline.py`)

* [ ] Retrieval → Refusal → Generation
* [ ] refusal short-circuit
* [ ] retrieval-only skips generation
* [ ] telemetry per stage

### RetrievalStage (`tests/unit/rag/test_retrieval_stage.py`)

* [ ] embedding cache key correct
* [ ] cache hit/miss behavior
* [ ] top_k=20
* [ ] namespace + RBAC filters applied
* [ ] rerank top_n=5
* [ ] preserve cosine + rerank

### RefusalStage (`tests/unit/rag/test_refusal_stage.py`)

* [ ] injected threshold
* [ ] >= semantics incl equal
* [ ] refusal includes top 3 sources + LOW_SIMILARITY
* [ ] no DB imports, no internal default

### GenerationStage (`tests/unit/rag/test_generation_stage.py`)

* [ ] 1500 token context budget
* [ ] no runtime SimHash
* [ ] retrieval-only skip LLM
* [ ] streaming + fallback
* [ ] 500 output token budget (max)
* [ ] citations mapped
* [ ] confidence from cosine only
* [ ] confidence bands correct

### RAG Structural Purity (`tests/unit/rag/test_no_db_imports.py`) **[V1.6 OPTIONAL]**

* [ ] no DB/repo imports in rag layer

---

## 9.4 Chunking Subsystem Tests

### TokenChunker (`tests/unit/rag/chunking/test_chunker.py`)

* [ ] 512-token chunks + 50-token overlap
* [ ] max 200 chunks/file enforced
* [ ] empty files safe

### LineMapper (`tests/unit/rag/chunking/test_line_mapper.py`)

* [ ] start_line/end_line required
* [ ] 1-indexed line numbers
* [ ] correct spans

### Normalizer (`tests/unit/rag/chunking/test_normalizer.py`)

* [ ] lowercase outside code blocks
* [ ] preserve inside fenced code blocks
* [ ] collapse whitespace outside code blocks
* [ ] strip markdown markers outside code blocks only

### SimHashDedupe (`tests/unit/rag/chunking/test_simhash.py`)

* [ ] identical detected (0)
* [ ] near-duplicate detected (<=3)
* [ ] different not flagged (>3)
* [ ] uses normalized text
* [ ] ingestion-only

---

## 9.5 Retrieval Subsystem Tests

### QueryEmbedder (`tests/unit/rag/retrieval/test_embedder.py`)

* [ ] cache key sha256(query+model_id+index_version)
* [ ] TTL default 24h
* [ ] cache hit bypasses API
* [ ] cache miss calls embed API (mocked)
* [ ] 768-d vector enforced
* [ ] API failure error mapping

### VectorStoreClient (`tests/unit/rag/retrieval/test_vector_store.py`)

* [ ] top_k results include cosine score + metadata
* [ ] namespace + RBAC filters applied
* [ ] upsert batches (100 max)
* [ ] metadata required fields:

  * repo, file_path, source_type, commit_sha
  * start_line, end_line
  * chunk_hash, model_id, index_version
  * visibility, allowed_user_ids
* [ ] types validated
* [ ] default visibility private if unspecified
* [ ] visibility consistency:

  * public ⇒ allowed_user_ids == []
  * private ⇒ allowed_user_ids non-empty
  * shared ⇒ allowed_user_ids non-empty **[V2 OPTIONAL]**

### CrossEncoderReranker (`tests/unit/rag/retrieval/test_reranker.py`)

* [ ] model cached
* [ ] scoring works
* [ ] top_n=5
* [ ] latency tracked

### Runtime Retrieval Deduplication (`tests/unit/rag/retrieval/test_runtime_dedupe.py`) **[OPTIONAL]**

* [ ] near-duplicates suppressed
* [ ] deterministic policy

---

## 9.6 Generation Subsystem Tests

### PromptBuilder (`tests/unit/rag/generation/test_prompt_builder.py`)

* [ ] groundedness rules included
* [ ] [Source N] citation format enforced
* [ ] includes question + context
* [ ] context budget enforced

### AnswerGenerator (`tests/unit/rag/generation/test_answer_generator.py`)

* [ ] correct model + params
* [ ] SSE token streaming (answer mode only)
* [ ] TTFT measured
* [ ] total time measured
* [ ] LLM outage => retrieval-only mode (no tokens)

### CitationMapper (`tests/unit/rag/generation/test_citation_mapper.py`)

* [ ] [Source N] extracted
* [ ] N maps to context_chunks[N-1]
* [ ] includes file_path, source_url (nullable), start_line, end_line
* [ ] missing source handled

### ConfidenceCalculator (`tests/unit/rag/generation/test_confidence_calculator.py`)

* [ ] cosine >=0.85 => HIGH
* [ ] cosine >=0.70 and <0.85 => MEDIUM
* [ ] cosine <0.70 => LOW
* [ ] uses cosine only
* [ ] empty candidates safe

---

## 9.7 Connectors Tests

### GitHubClient (`tests/unit/connectors/test_github_client.py`)

* [ ] repo tree fetch
* [ ] file content fetch/decode
* [ ] scoped token auth
* [ ] rate limit respected
* [ ] 404 handled

### GitDiffScanner (`tests/unit/connectors/test_diff_scanner.py`)

* [ ] added/modified/deleted detected
* [ ] rename mapping old→new
* [ ] empty diff safe

### IgnoreRules (`tests/unit/connectors/test_ignore_rules.py`)

* [ ] .librarianignore loaded
* [ ] builtin blacklist applied
* [ ] gitignore pattern matching correct

### FileSizeValidator (`tests/unit/connectors/test_file_validator.py`)

* [ ] <=1MB accepted; >1MB rejected
* [ ] size check before content fetch

### GitHubExtractor (`tests/unit/connectors/test_extractor.py`)

* [ ] base64 decode to UTF-8
* [ ] binary skipped
* [ ] empty safe
* [ ] API errors mapped

---

## 9.8 Workers Tests

### IngestJobTask (`tests/unit/workers/test_ingest_task.py`)

* [ ] fetch → chunk → embed → upsert → store
* [ ] ignore rules + limits enforced
* [ ] SimHash dedupe
* [ ] embeddings batched (64)
* [ ] atomic Source metadata update only after success
* [ ] failure leaves Source unchanged
* [ ] retries: 3 exponential backoff

### PurgeJobTask (`tests/unit/workers/test_purge_task.py`)

* [ ] delete vectors by file_path
* [ ] delete chunk rows
* [ ] namespace scoped
* [ ] batch purge
* [ ] logged

### ReindexJobTask (`tests/unit/workers/test_reindex_task.py`)

* [ ] namespace swap (free tier)
* [ ] validate before swap
* [ ] swap only after validation
* [ ] rollback on swap failure
* [ ] delete old namespace after success

### BackupJobTask (`tests/unit/workers/test_backup_task.py`)

* [ ] pg_dump + gzip + upload
* [ ] prune >7 days
* [ ] logged

### HeartbeatTask (`tests/unit/workers/test_heartbeat_task.py`) **[V1.6 OPTIONAL]**

* [ ] write heartbeat key + TTL=90s
* [ ] schedule every 30s
* [ ] redis failure logged, worker continues

---

## 9.9 Persistence Layer Tests

### UsersRepository (`tests/unit/db/test_users_repo.py`)

* [ ] get by id
* [ ] get by email
* [ ] not found returns None

### SourcesRepository (`tests/unit/db/test_sources_repo.py`)

* [ ] create with index metadata
* [ ] retrieve by namespace
* [ ] atomic update supports rollback
* [ ] last_indexed_sha updated only after success
* [ ] index_model_id + index_version stored
* [ ] paid-tier index_name stored if used

### ChunksRepository (`tests/unit/db/test_chunks_repo.py`)

* [ ] create chunk
* [ ] retrieve by vector_ids
* [ ] delete by file_path + namespace
* [ ] batch delete multi-file

### QueryLogsRepository (`tests/unit/db/test_query_logs_repo.py`)

* [ ] store prompt_hash + redacted prompt (no PII)
* [ ] store retrieved chunk IDs + cosine scores
* [ ] store refusal reason nullable
* [ ] store latency fields: t_embed_ms, t_vector_ms, t_rerank_ms, t_total_ms
* [ ] t_llm_ttft_ms nullable: NULL on refusal/retrieval-only

### ThresholdsRepository (`tests/unit/db/test_thresholds_repo.py`)

* [ ] get by namespace+index_version
* [ ] update
* [ ] default 0.65 if not set

### FeedbackRepository (`tests/unit/db/test_feedback_repo.py`)

* [ ] create linked to query_log_id
* [ ] rating integer 1 or -1
* [ ] optional comment stored
* [ ] retrieve by query_log_id
* [ ] not found returns None

### EvaluationRepository (`tests/unit/db/test_evaluation_repo.py`)

* [ ] EvaluationRun created w/ dataset version
* [ ] per-question results stored
* [ ] taxonomy label stored
* [ ] multiple runs preserved
* [ ] aggregate metrics stored
* [ ] latest run retrievable without overwriting history

### IngestRunsRepository (`tests/unit/db/test_ingest_runs_repo.py`) **[V1.6 OPTIONAL]**

* [ ] create run pending with UUID
* [ ] update status running/completed/failed
* [ ] finalize transaction safe
* [ ] unfinalized does not affect Source metadata

---

## 9.10 Core Utilities Tests

### Settings (`tests/unit/core/test_config.py`)

* [ ] env vars load
* [ ] model IDs match DECISIONS values
* [ ] chunking params correct (512/50)
* [ ] retrieval params correct (top_k=20, top_n=5)
* [ ] threshold default 0.65
* [ ] rate limits correct (50/hr, 5 streams)
* [ ] ingestion limits correct (1MB, 200 chunks)

### Logging (`tests/unit/core/test_logging.py`)

* [ ] structured JSON logs
* [ ] auth headers stripped
* [ ] API keys masked
* [ ] PII redaction in prompts
* [ ] no full file content logged

### Errors (`tests/unit/core/test_errors.py`)

* [ ] 409 mismatch mapping correct (includes canonical codes + details fields: `expected_model_id`, `expected_index_version`, `received_model_id`, `received_index_version`)
* [ ] refusal maps to 200 SSE mode=refusal (no tokens)
* [ ] retrieval-only maps to 200 SSE mode=retrieval_only (no tokens)
* [ ] auth 401, forbidden 403, rate limit 429, internal 500
* [ ] expected vs received fields present when applicable

### Telemetry (`tests/unit/core/test_telemetry.py`)

* [ ] OTel spans per stage
* [ ] stage latencies recorded
* [ ] context propagated

### Security (`tests/unit/core/test_security.py`) **[REQUIRED]**

* [ ] AES-256 encrypt/decrypt PAT
* [ ] different tokens produce different ciphertext
* [ ] key rotation supported
* [ ] bcrypt hash + verify
* [ ] JWT claims + validation + expiry behavior

### Caching (`tests/unit/core/test_caching.py`)

* [ ] Redis SET/GET with TTL
* [ ] cache miss returns None
* [ ] TTL expiry respected
* [ ] Redis unavailable returns None (no exception)
* [ ] embedding cache key correctness
* [ ] retrieval cache key correctness if implemented (RBAC isolation)

### Middleware (`tests/unit/core/test_middleware.py`)

* [ ] X-Request-ID injected
* [ ] correlation ID propagated/generated
* [ ] request timing measured
* [ ] does not alter body
* [ ] strips sensitive headers from logs

---

# 10) Frontend Tests

## 10.1 Components

### QueryInput (`tests/frontend/components/test_query_input.tsx`)

* [ ] empty input validation
* [ ] valid input enables submit
* [ ] submit triggers API call
* [ ] rate limit warning shown near limit
* [ ] estimated cost displayed

### StreamingAnswer (`tests/frontend/components/test_streaming_answer.tsx`)

* [ ] SSE connection opens
* [ ] start event handled (captures query_log_id + mode)
* [ ] parses multi-line SSE messages by concatenating `data:` lines with `\n` then `JSON.parse`
* [ ] ignores SSE comment lines beginning with `:` and other non-`data:` lines safely
* [ ] answer mode: tokens appended to output live (exact concatenation)
* [ ] refusal/retrieval-only: no tokens; UI renders sources + reason only
* [ ] completion event triggers finalize UI
* [ ] error event shows fallback UI
* [ ] connection closed after completion
* [ ] unmount/cleanup closes connection (backend integration verifies active stream gauge decremented)

### CitationPanel (`tests/frontend/components/test_citation_panel.tsx`)

* [ ] shows file_path + line range
* [ ] snippet truncated properly
* [ ] source_url clickable when non-null
* [ ] empty safe

### ConfidenceBadge (`tests/frontend/components/test_confidence_badge.tsx`)

* [ ] HIGH/MEDIUM/LOW badges correct
* [ ] tooltip explains meaning

### ThumbsFeedback (`tests/frontend/components/test_thumbs_feedback.tsx`)

* [ ] thumbs up sends feedback=1
* [ ] thumbs down sends feedback=-1
* [ ] includes query_log_id
* [ ] visual confirmation
* [ ] failure handling

## 10.2 Admin Components (`tests/frontend/components/admin/`)

* [ ] IngestForm validation + submit
* [ ] SourceList paginated + delete confirm
* [ ] ThresholdTuner change + submit
* [ ] AnalyticsDashboard renders metrics
* [ ] IngestRunMonitor polls status
* [ ] non-admin redirected to access denied

## 10.3 Hooks (`tests/frontend/hooks/`)

* [ ] useSSEStream: connects, parses multi-line SSE messages, ignores comments, handles start/token/complete/error, cleans up
* [ ] useQuery: payload correctness + state transitions
* [ ] useAuth: returns claims / unauth state

## 10.4 Auth Flow (`tests/frontend/auth/`)

* [ ] protected routes redirect unauth to login
* [ ] admin routes redirect non-admin to denied
* [ ] login stores session + redirects
* [ ] expiry triggers re-auth
* [ ] logout clears session

---

# 11) Integration Tests

## 11.1 API Integration (`tests/integration/test_api.py`)

* [ ] full query flow: auth → rate limit → query → SSE
* [ ] SSE validates headers + framing + start/token/complete ordering
* [ ] SSE parsing validates multi-line data concatenation then JSON parse; ignores comment lines beginning with `:`
* [ ] answer mode emits tokens; complete contains metadata only (no full answer)
* [ ] answer mode empty string behavior: zero tokens permitted only for empty answer; `confidence MUST NOT be HIGH`
* [ ] refusal emits no tokens; complete includes LOW_SIMILARITY + sources
* [ ] retrieval-only emits no tokens; complete includes BUDGET_EXCEEDED or LLM_UNAVAILABLE + sources
* [ ] ingest flow: admin auth → validation → job create
* [ ] invalid auth rejected at boundary
* [ ] CORS headers present
* [ ] feedback integration: submit feedback then verify stored link
* [ ] client disconnect closes stream and decrements `librarian_active_sse_streams`

## 11.2 RAG Pipeline Integration (`tests/integration/test_rag_pipeline.py`)

* [ ] end-to-end query with mocked OpenAI/Pinecone
* [ ] threshold injected from Domain
* [ ] RBAC filtering works
* [ ] refusal flow works
* [ ] retrieval-only mode works
* [ ] cache hit vs miss yields latency difference

## 11.3 Ingestion Integration (`tests/integration/test_ingestion.py`)

* [ ] incremental sync: new ingested, deleted purged
* [ ] rename detection handled
* [ ] simhash dedupe applied
* [ ] Source metadata updated only after success
* [ ] failure does not update Source
* [ ] default visibility private

## 11.4 Migrations Integration (`tests/integration/test_migrations.py`)

* [ ] migrations apply cleanly
* [ ] schema matches models
* [ ] indexes + FKs correct
* [ ] downgrade leaves valid prior schema

## 11.5 Blue-Green Reindex (`tests/integration/test_reindex.py`)

* [ ] namespace swap succeeds
* [ ] validation gating works
* [ ] no swap on validation failure
* [ ] queries during reindex use old namespace

## 11.6 Health (`tests/integration/test_health.py`)

* [ ] health: Postgres+Redis up => 200
* [ ] Pinecone down still health 200 (core-only)
* [ ] ready endpoint tested only if exists

## 11.7 Load Shedding (`tests/integration/test_load_shedding.py`) **[OPTIONAL UNTIL IMPLEMENTED]**

* [ ] activates on p95 >2.5s 3 windows or CPU>80%
* [ ] rejects non-critical with 429/503
* [ ] admin/ingest continue
* [ ] auto-deactivate

## 11.8 Data Retention (`tests/integration/test_data_retention.py`) **[REQUIRED WHEN ENABLED IN PROD CONFIG]**

* [ ] purge query logs >90d
* [ ] purge feedback with log
* [ ] evaluation-flagged exempt
* [ ] configurable retention
* [ ] does not delete within window

## 11.9 Audit Logging (`tests/integration/test_audit_logging.py`) **[REQUIRED WHEN ENABLED IN PROD CONFIG]**

* [ ] role change writes audit row
* [ ] source update writes audit row
* [ ] threshold update writes audit row
* [ ] append-only
* [ ] retention >=14d

---

# 12) Evaluation Tests

## 12.1 Golden Questions (`tests/evaluation/test_golden_questions.py`)

* [ ] run all questions
* [ ] refusals counted as abstention
* [ ] compute precision/recall/F1
* [ ] refusal rate computed
* [ ] compare to environment gate targets
* [ ] report generated per run

## 12.2 Latency Benchmarks (`tests/evaluation/test_latency.py`)

* [ ] p50 ≤1s
* [ ] p95 ≤2s
* [ ] p99 ≤3s
* [ ] embedding cache hit <100ms
* [ ] embedding cache miss 200–500ms
* [ ] vector p95 ≤300ms (soft)
* [ ] rerank p95 ≤400ms (soft)
* [ ] TTFT ≤500ms (requirement)
* [ ] LLM total 500–1500ms (soft)

## 12.3 Cost Tracking (`tests/evaluation/test_cost_tracking.py`)

* [ ] embedding + LLM costs calculated correctly
* [ ] total cost/query <$0.01
* [ ] monthly spend projection correct

## 12.4 Error Codes (`tests/evaluation/test_error_codes.py`)

* [ ] 409 for model/version mismatch (JSON, not SSE)
* [ ] 200 SSE for refusal (mode=refusal, no tokens)
* [ ] 200 SSE for retrieval-only (mode=retrieval_only, no tokens)
* [ ] 401/403/429/500 correct mappings

## 12.5 PQS (`tests/evaluation/test_pqs.py`)

* [ ] dataset loads
* [ ] runner executes all queries
* [ ] store latency + mode + cosine score
* [ ] aggregate p50/p95/p99 computed
* [ ] refusal rate within expected bounds
* [ ] results persisted for trend

---

# 13) Test Data Requirements

## 13.1 Golden Question Set

* [ ] 50–100 questions with ground-truth sources
* [ ] spans high/medium/low similarity
* [ ] includes ambiguous, rare, multi-source, code-specific

## 13.2 Test Repositories

* [ ] small (<100 files)
* [ ] medium (100–1000)
* [ ] large (>1000)
* [ ] varied file types (.md, .txt, .rst)
* [ ] includes `.librarianignore`

## 13.3 Mock Data

* [ ] users: admin/user
* [ ] sources: dev/staging/prod namespaces
* [ ] chunks: scores 0.5–1.0
* [ ] query logs with feedback

---

# 14) Test Execution

**Unit**

```bash
pytest tests/unit/ -v --cov=app --cov-report=html
```

**Integration**

```bash
pytest tests/integration/ -v
```

**Evaluation**

```bash
pytest tests/evaluation/ -v
```

**All**

```bash
pytest -v --cov=app --cov-report=html
```

---

## 15) “To Canonize” Checklist

If you want v1.6 optional invariants to become hard requirements, promote them into DECISIONS/Architecture first:

* No DB imports in RAG layer
* ingest_run_id atomic finalize model
* heartbeat key format + readiness gating
* confidence band thresholds
* token budgets (1500/500) and cache TTL defaults (24h) if you want them stable across environments

---

**Document Owner:** Engineering Team
**Last Updated:** March 12, 2026 (v1.9.0)
