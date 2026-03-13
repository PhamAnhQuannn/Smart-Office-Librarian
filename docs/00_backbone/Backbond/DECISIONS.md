## ✅ DECISIONS — Smart Office Librarian (Single Source of Truth)

**Version:** v1.5
**Status:** Active (Production-Ready Budget MVP)
**Last Updated:** 2026-03-10
**Owner:** Project Maintainer

This document is the only canonical reference for system-wide decisions. If any other doc conflicts with this one, this file wins.

---

## 1) Deployment Philosophy

**Goal:** Monthly cost $18–$25 (Lightsail 2GB + Managed Vector DB Free Tier).
**v1 Focus:** GitHub ingestion + high-precision RAG + RBAC.

---

## 2) Environments & Isolation

| Environment | Purpose    | Pinecone Namespace |
| ----------- | ---------- | ------------------ |
| dev         | Local Dev  | dev                |
| staging     | CI/CD Test | staging            |
| prod        | Lightsail  | prod               |

**Namespace Composition Rule (v2 Ready):**

* v1: `namespace = "{env}"`
* Planned v2: `namespace = "{env}:{tenant_id}"`

---

## 3) Model & Provider Decisions

* **Embeddings:** OpenAI `text-embedding-3-small` (768d)

  * **Model ID:** `text-embedding-3-small-v1`
* **LLM:** OpenAI `gpt-4o-mini`

  * **Model ID:** `gpt-4o-mini`
* **Reranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (Self-hosted on CPU)

---

## 4) Vector DB & Safety

* **Provider:** Pinecone Free Tier (1 index, ~100k vectors)
* **Metric:** cosine

### 4.1 Cross-Version Safety (Hard Rule)

A query MUST match the stored:

* `model_id`
* `index_version`

**Canonical:**

* `index_version = 1` (integer-based versioning)

**Mismatch Behavior (System Error Codes):**

* If `model_id` mismatch → `EMBEDDING_MODEL_MISMATCH`
* If `index_version` mismatch → `INDEX_VERSION_MISMATCH`

**API Contract for Mismatch Errors:**

* Return **HTTP 409** with:

  * `error_code` = (`EMBEDDING_MODEL_MISMATCH` | `INDEX_VERSION_MISMATCH`)
  * `message` (human-readable)
  * `expected_model_id`, `expected_index_version`
  * `received_model_id`, `received_index_version`
* Log as system error event.

---

## 5) Canonical Metadata & Chunking Schema

### 5.1 Identity & RBAC (Canonical v1)

Every chunk MUST include:

* `allowed_user_ids: string[]` (MVP: explicitly allowed based on GitHub repository access)
* `visibility: public | private`

**RBAC Retrieval Filter (Canonical Semantics):**

* Apply metadata filter equivalent to:

  * `(visibility == "public") OR (allowed_user_ids $in [current_user.id])`

(Do NOT implement as substring match or naive "contains" on strings. This matches ARCHITECTURE.md Invariant D.)

### 5.2 Source & Line Mapping

* `chunk_max_tokens = 512`
* `chunk_overlap_tokens = 50`

**Line Numbers:** `start_line` and `end_line` are required.

**Mapping Strategy (Canonical):**

1. Split raw file into lines
2. Group lines into chunks until token limit reached
3. Store line range in metadata (`start_line`, `end_line`)

---

## 6) Data Lifecycle & Ingestion

### 6.1 Sync State

Postgres stores:

* `sources.last_indexed_sha`

### 6.2 Rename Handling (Canonical)

File identity is tracked via `file_path`.

On git diff detection of a rename, the system MUST:

1. Delete vectors associated with `old_path`
2. Delete Postgres chunk metadata rows associated with `old_path`
3. Ingest `new_path` as a fresh entry

### 6.3 Deduplication

* **Method:** SimHash
* **Threshold:** 3 bits distance
* **Policy:** No runtime dedupe required; ingestion-level SimHash ensures uniqueness.

### 6.4 Normalization for Hashing (Canonical)

1. Lowercase text
2. Collapse whitespace/newlines (**excluding fenced code blocks**)
3. Strip markdown markers (`#`, `*`) **only outside of code blocks** to preserve implementation meaning

---

## 7) Retrieval & RAG Pipeline

### 7.1 Pipeline Stages (Canonical)

* Vector Search: `top_k = 20`
* Rerank: reduce to `top_n = 5`
* **Ordering:**

  * Sort chunks by rerank score descending
  * For chunks from the same file, preserve original file line order
* Budget:

  * `context_tokens = 1500`
  * `response_tokens = 500`

### 7.2 Similarity Threshold Refusal

**Threshold Storage (Canonical):**
Thresholds are stored in PostgreSQL per environment/index to allow runtime tuning without redeploy.

* `SIMILARITY_THRESHOLD_REFUSE` (Initial Default: `0.65`)

**Comparison Operator (Canonical):**

* The system uses **greater-than-or-equal (>=)** semantics for threshold comparison.
* A chunk with `cosine_score >= threshold` is considered sufficient confidence to permit generation.
* A chunk with `cosine_score < threshold` triggers refusal mode.

**Calibration Rule (Canonical):**

* Threshold tuned to maximize **F1 score** on the “Golden Question” evaluation set.

### 7.3 API Refusal Contract (Hard Rule)

If top chunk score < threshold:

* Return **HTTP 200**
* Include:

  * `refusal_reason: "LOW_SIMILARITY"`
  * `answer: null` (or empty string; choose one and keep consistent)
  * `sources`: Top-3 retrieved snippets (retrieval-only mode)
* Log retrieval failure event for dashboard analysis.

**Canonical Source/Snippet Object Schema:**
Each item in `sources[]` MUST include:

* `file_path`
* `source_url`
* `start_line`
* `end_line`
* `text` (may be truncated to a safe display length)

---

## 8) Performance & Latency Budgets (Soft)

To meet p95 ≤ 2.0s, internal soft budgets:

* Vector Search: ≤ 300ms

  * Note: Pinecone free tier may spike to ~1s on cold access
* Reranking: ≤ 400ms

  * Monitored for CPU spikes on 2GB VPS
* LLM TTFT: ≤ 600ms
* Total Pipeline (pre-generation): ≤ 1.0s

### 8.1 Realism Under Load (Hard Truth)

Worst case (budget MVP assumption):

* 5 users
* Each fires 2 queries concurrently
* Reranker CPU spikes
* Pinecone cold start

On 2GB VPS:

* CPU may hit 85–95%
* Latency may reach ~2.5s p95 temporarily

Mitigations:

* Reranker batch fallback (Section 10)
* Refusal logic
* Cost caps + retrieval-only mode

This is acceptable for $18–$25/month architecture.

### 8.2 Caching Policy (Redis)

* Retrieval Results TTL: `60s`
* Embedding Cache TTL: `24h`

**Cache Invalidation / Staleness Rule (Canonical):**
Retrieval cache key MUST include:

* `namespace + repo + index_version + sources.last_indexed_sha`

This prevents serving stale retrieval results after ingestion updates.

---

## 9) Logging & Privacy

### 9.1 Evaluation-Safe Logging (Canonical)

`query_logs` stores:

* `prompt_hash (sha256)`
* `redacted_prompt` (PII stripped)
* `retrieved_chunk_ids + similarity_scores`
* `user_feedback (1/-1)`
* `refusal_reason` (nullable)

**Stage Latencies (Canonical fields):**

* `t_embed_ms`
* `t_vector_ms`
* `t_rerank_ms`
* `t_llm_ttft_ms` (nullable if refusal or LLM disabled)
* `t_total_ms`

These fields are required to measure p95 targets.

### 9.2 Secrets

* Secrets stored in `.env` (Prod: `chmod 600`)
* NEVER log Authorization headers or raw provider tokens

---

## 10) Ingestion Limits

* Max File Size: `1MB`
* Max Chunks per File: `200`

**Batching:**

* Embedding: `64` chunks per request
* Reranker: single batch of `20` chunks

  * fallback to `10` if CPU utilization > 80%

---

## 11) Rate Limiting & Operational Controls (Canonical)

**Maximum Query Rate (Canonical):**

* `MAX_QUERY_RATE_PER_USER = 50` requests per rolling 1-hour window
* Applies to authenticated users submitting queries (`POST /api/v1/query`)
* This is the single source of truth for query rate limiting (per REQUIREMENTS.md FR-5.1)

**Concurrency (Canonical):**

* `MAX_CONCURRENT_STREAMS_PER_USER = 5` active query streams
* Applies to originating query streams (not GET attachment views)

**Implementation:**

* Storage: Redis sliding window
* On rate limit exceeded: return HTTP 429 with `error_code="RATE_LIMIT_EXCEEDED"`
* On concurrency exceeded: return HTTP 429 with `error_code="RATE_LIMIT_CONCURRENCY_EXCEEDED"`


