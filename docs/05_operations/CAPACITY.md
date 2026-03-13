# Capacity Planning Documentation

**Version:** v1.6  
**Status:** Production Capacity Planning  
**Last Updated:** 2026-03-11  
**Compliance:** REQUIREMENTS.md NFR-1.x/NFR-2.x, TECH_STACK.md v1.2, OPERATIONS.md Section 7, DECISIONS.md v1.5  

> This document defines capacity planning, resource limits, scaling triggers, guardrails, and upgrade paths for the Smart Office Librarian RAG system to ensure reliable performance and cost-effective growth.

---

## Overview

Capacity planning ensures the system can handle expected load while maintaining SLO targets and controlling costs. This document establishes:

* **Current Capacity:** MVP deployment resource limits and baseline performance
* **Scaling Triggers:** Thresholds that indicate capacity expansion is needed
* **Key Metrics:** Metrics to monitor for capacity decisions
* **Resource Limits:** Hard limits and bottlenecks in current architecture
* **Guardrails:** Automatic degraded-mode controls (CPU/memory/LLM budget)
* **Upgrade Paths:** Migration strategies for growth scenarios (including vector tier upgrades)
* **Forecasting:** Simple methods to predict when limits will be hit
* **Runbook Precision:** Explicit windows, sustained definitions, and safe operational actions

**Capacity Planning Principles:**

* **Measure continuously:** Track resource utilization and performance metrics
* **Scale proactively:** Expand capacity before hitting hard limits
* **Cost-aware:** Balance performance needs with budget constraints
* **Document baselines:** Establish performance baselines for comparison
* **Plan migration:** Have clear upgrade paths defined before needing them

---

## 0. Canonical Notes (Non-Negotiable)

This doc is aligned to **DECISIONS.md (Single Source of Truth)**. If another document conflicts, DECISIONS.md wins.

### 0.1 Operational vs. Architectural Limits

Some NFR targets are **architectural goals** (what the system design supports) but the **budget MVP** has **operational caps** due to the chosen stack.

* **Architectural Retrieval Scale Target (NFR-1.2):** up to **200k chunks** with retrieval p95 ≤ 500ms (requires upgraded vector tier).
* **Operational Pinecone Free Tier Cap (TECH_STACK v1.2):** **≤ 100k vectors** total.
* **Chunk ↔ Vector Rule:** **1 chunk = 1 vector** (operational assumption).

✅ Therefore, **budget MVP operational limit is ~100k chunks/vectors** unless Pinecone is upgraded.

### 0.2 Window Definitions (How “Sustained” Is Measured)

To avoid ambiguity, this document uses the following canonical definitions:

* **CPU sustained for X minutes:** rolling **average** CPU utilization over the last **X minutes** (evaluated every 1 minute).
* **Memory sustained for X minutes:** rolling **average** memory utilization over the last **X minutes** (evaluated every 1 minute).
* **Latency p95 sustained for X minutes:** p95 computed over a rolling **X-minute window**, evaluated every 1 minute.
* **Provider error rate sustained for X minutes:** (errors / total requests) computed over a rolling **X-minute window**, evaluated every 1 minute.

### 0.3 SEV Override Rule (Incidents Beat Cooldowns)

If a condition is classified as **SEV-1** (OOM risk, disk exhaustion risk, data corruption risk), the system may **override guardrail cooldown rules** and take immediate protective action.

### 0.4 Guardrails vs Scaling Triggers (No Conflict)

* **Guardrails (Section 9)** are **fast-reacting**, protective controls intended to keep the system alive (minutes-level).
* **Scaling triggers (Section 3)** are **capacity planning signals** intended to drive upgrade decisions (tens of minutes to hours-level).

Guardrails may activate **before** a scaling trigger is reached.

---

## 1. Current Deployment Capacity (MVP Configuration)

### 1.1 Infrastructure Specifications

**Amazon Lightsail VPS (Single Instance):**

* **CPU:** 1 vCPU (shared)
* **Memory:** 2 GB RAM
* **Storage:** 60 GB SSD
* **Network:** 2 TB data transfer included
* **Cost:** $10/month base

**Services on VPS (Docker Compose):**

* FastAPI backend (Uvicorn)
* Celery worker (background jobs)
* PostgreSQL 15 (metadata, logs)
* Redis 7 (cache, broker)
* Caddy (reverse proxy, HTTPS)
* (Optional) Next.js frontend served via Caddy

### 1.2 Target Load Profile (MVP)

**User Concurrency (per REQUIREMENTS NFR-2.3):**

* **MVP Target:** ≤ 100 concurrent active users
* **v2 Target:** 500+ concurrent users (requires upgrade)

**Query Load:**

* **Sustained QPS:** ≤ 10 QPS (design SLO envelope per NFR-1.1; see Workload Assumptions below)
* **Peak QPS:** ~20 QPS burst for short periods (< 1 minute)
* **Queries per User:** 50/hour rate limit (per DECISIONS.md §11)
* **Monthly Query Volume:** ~5k–10k queries (light usage, 100 users)

**Ingestion Load:**

* **Throughput Target:** ≥ 200 documents/minute (per REQUIREMENTS NFR-1.4; workload-dependent)
* **Typical Batch:** 50–100 documents per repository
* **Ingestion Frequency:** Weekly scheduled + on-demand
* **Ingestion Policy:** Ingestion should be scheduled off-peak when possible to protect query SLOs.

**Index Size**

* **Operational MVP Target (Free Tier Safe):** **≤ 80k vectors**
* **Operational MVP Hard Cap:** **≤ 100k vectors**
* **Architectural Target (requires upgrade):** **200k+ chunks** (NFR-1.2) and **1M+ chunks** (NFR-2.2 v2)

### 1.3 Workload Assumptions (Required for Capacity Math)

These assumptions determine whether the system can meet SLOs on the budget MVP stack:

* **Average retrieval set:** top_k=20 → rerank to top_n=5 (DECISIONS.md §7.1)
* **Context budget:** 1500 tokens; response budget 500 tokens (DECISIONS.md §7.1)
* **Cache hit rates (targets):**
  * **Embedding cache hit ratio:** ≥ 30% (goal), ≥ 40% (optimized)
  * **Retrieval cache hit ratio:** environment-dependent; TTL 60s (DECISIONS.md §8.2)
* **Answer mix (typical goal):**
  * ≥ 60% normal “generate” answers
  * ≤ 30% refusals / retrieval-only (low similarity or budget caps)
  * ≤ 10% long/complex answers (worst-case SSE duration)
* **Ingestion overlap:** ingestion during peak query hours increases risk of p95 SLO breaches; default is off-peak.

---

## 2. Performance Baselines (MVP)

### 2.1 Query Latency Budgets (Soft Targets)

To meet **p95 ≤ 2.0s** (NFR-1.1), internal soft budgets:

* **Query embedding:** ≤ 120ms p95 (cached or small input)
* **Vector search:** ≤ 300ms p95 (Pinecone; may spike on cold start)
* **Reranking:** ≤ 400ms p95 (CPU-bound on 1 vCPU)
* **LLM TTFT (soft budget):** ≤ 600ms p95 (provider-dependent)
* **Total end-to-end p95 target:** ≤ 2.0s

> Note: **TTFT failover** (Section 9.3) is a **hard availability guardrail** and may be higher than the soft TTFT budget. The soft budget is for performance tuning; the guardrail prevents worst-case provider latency from consuming the total latency envelope.

### 2.2 Observed Baselines (MVP Load)

**Important:** These baselines are only valid within the **free-tier safe region (≤ 80k vectors)** and under the measurement conditions specified below. Performance at **200k+ chunks** requires an upgraded vector tier and may require additional CPU capacity.

#### 2.2.1 Baseline Measurement Conditions (Required for Validity)

Record the following whenever baselines are updated:

* **vectors_total:** TBD (target measurement points: 10k / 50k / 80k)
* **concurrent_active_users:** TBD
* **sse_streams_active_peak:** TBD
* **cache_hit_ratio:** embedding TBD, retrieval TBD
* **ingestion_state:** on/off (recommended: off for query baselines)
* **pinecone_state:** warm/cold access included/excluded (must be declared)
* **prompt_size_distribution:** small/typical/large (must be declared)
* **context_usage:** median context tokens vs 1500 budget (must be declared)

#### 2.2.2 Query Latency (Measured at MVP Load)

* **p50 End-to-End:** ~800ms
* **p95 End-to-End:** ≤ 2.0s
* **p99 End-to-End:** ~3.5s
* **Retrieval (p95):** ≤ 500ms (at ≤80k vectors)
* **TTFT (p95):** ≤ 500ms

#### 2.2.3 Ingestion Performance (Workload-dependent)

* **Documents Processed:** 180–220 docs/minute (typical)
* **Chunk Creation Rate:** ~1000 chunks/minute
* **Embedding Batch Size:** 50 chunks per embedding request (configurable)

#### 2.2.4 Resource Utilization (Typical)

* **CPU:** 40–60% average, 80% peak during ingestion
* **Memory:** 1.2–1.5 GB used
* **Disk I/O:** 10–20 MB/s during ingestion
* **Network:** 5–15 Mbps typical

---

## 3. Scaling Triggers (When to Upgrade)

### 3.1 Resource-Based Triggers (CRITICAL)

**CPU Saturation:**

* **Warning:** CPU > 70% sustained for 60 minutes
* **Critical:** CPU > 80% sustained for 15 minutes (load shedding per NFR-1.5)
* **Action:** Apply guardrails (Section 9), then upgrade to 4GB Lightsail or migrate to ECS

**Memory Pressure:**

* **Warning:** Memory > 80% sustained for 15 minutes
* **Critical:** Memory > 90% sustained for 5 minutes (OOM risk)
* **Action:** Apply guardrails (Section 9), then upgrade instance or tune memory allocations

**Disk Space:**

* **Warning:** Disk usage > 80% sustained for 15 minutes
* **Critical:** Disk usage > 90% sustained for 5 minutes
* **Action:** Execute disk procedure (Section 10.3), then expand disk or offload data/logs

**Database Connection Pool Saturation:**

* **Warning:** Connection pool > 80% utilized (pool size 10) sustained for 15 minutes
* **Critical:** Connection exhaustion causing query failures OR pool at 100% sustained for 5 minutes
* **Action:** Tune pool + queries; if persistent, migrate Postgres to RDS

**Database Slow Queries (New):**

* **Warning:** `postgres_query_duration_seconds` p95 > 200ms sustained for 30 minutes
* **Critical:** `postgres_query_duration_seconds` p95 > 500ms sustained for 15 minutes OR query timeouts observed
* **Action:** identify query regressions, add indexes, reduce log table scans, and/or migrate Postgres to RDS

### 3.2 Performance-Based Triggers

**Query Latency SLO Breach:**

* **Warning:** p95 > 2.0s sustained for 60 minutes
* **Critical:** p95 > 2.5s sustained for 15 minutes
* **Action:** Identify bottleneck stage; apply guardrails; increase capacity

**Retrieval Latency Degradation:**

* **Warning:** Retrieval p95 > 700ms sustained for 15 minutes
* **Critical:** Retrieval p95 > 1.0s sustained for 10 minutes
* **Action:** Tune top_k/rerank policy; check Pinecone; consider vector tier upgrade

**Ingestion Backlog:**

* **Warning:** queue depth > 50 sustained for 60 minutes
* **Critical:** queue depth > 100 OR ingestion failures > 20% sustained for 30 minutes
* **Action:** Pause ingestion during peak; add worker capacity; upgrade instance

**Provider Throttling (GitHub/OpenAI/Pinecone):**

* **Warning:** 429/403 rate > 1% sustained for 10 minutes
* **Critical:** 429/403 rate > 5% sustained for 10 minutes
* **Action:** auto backoff + throttle; move ingestion off-peak; investigate account limits

### 3.3 Concurrency-Based Triggers

**User Concurrency:**

* **Warning:** > 80 concurrent active users sustained for 30 minutes
* **Critical:** > 100 concurrent users sustained for 15 minutes
* **Action:** Upgrade Tier 2 or horizontal scaling (Tier 3)

**SSE Saturation:**

* **Warning:** > 150 concurrent SSE streams sustained for 10 minutes
* **Critical:** > 200 concurrent SSE streams sustained for 5 minutes
* **Action:** apply SSE guardrails; add capacity; add instances

**Rate Limit Hit Rate:**

* **Warning:** > 10% requests return 429 for 30 minutes
* **Critical:** > 20% requests return 429 for 30 minutes
* **Action:** add capacity; increase rate limits only if budget allows

### 3.4 Cost-Based Triggers

**OpenAI API Budget:**

* **Warning:** budget utilization > 80%
* **Critical:** budget utilization = 100% (retrieval-only mode)
* **Action:** increase budget or reduce token usage (cache + smaller contexts/outputs)

**Pinecone Free Tier:**

* **Warning:** > 80k vectors indexed
* **Critical:** ≥ 100k vectors indexed
* **Action:** Pause ingestion + disable upserts + upgrade Pinecone or reduce scope

**Monthly Cost Overrun:**

* **Warning:** total monthly cost > $30
* **Critical:** total monthly cost > $50
* **Action:** identify drivers; enforce tighter budgets; increase plan only if approved

### 3.5 Data Growth Triggers

**Index Size:**

* **Warning:** > 80k vectors
* **Critical:** ≥ 100k vectors
* **Action:** archive sources or upgrade Pinecone

**Database Size vs Disk Risk:**

* **Warning:** DB size > 40 GB OR disk usage > 80%
* **Critical:** DB size > 50 GB OR disk usage > 90%
* **Note:** DB size is not equal to disk usage; Docker images/logs/backups consume disk.
* **Action:** enforce retention purges; archive logs; migrate to RDS + larger storage

**Redis Evictions:**

* **Warning:** eviction rate > 100 keys/min sustained for 10 minutes
* **Critical:** Redis memory > 90% configured limit sustained for 10 minutes
* **Action:** tune TTLs/keys; allocate more Redis memory if RAM allows; upgrade instance

---

## 4. Key Metrics to Measure

### 4.1 Resource Utilization

* `cpu_usage_percent`
* `memory_usage_bytes`
* `disk_usage_bytes`
* `disk_io_read_bytes_per_sec`, `disk_io_write_bytes_per_sec`

### 4.2 Performance

* `query_latency_seconds`
* `retrieval_latency_seconds`
* `ttft_seconds`
* `query_refusal_total`

**SSE (first-class):**

* `sse_streams_active` (must be aggregated across workers)
* `sse_stream_duration_seconds`
* `sse_tokens_streamed_total` (or `sse_bytes_streamed_total`)
* `sse_stream_cancellations_total`

### 4.3 Ingestion

* `ingestion_duration_seconds`
* `ingestion_docs_processed_total`
* `ingestion_chunks_created_total`
* `worker_queue_depth`
* `ingestion_paused_state` (gauge: 0/1, from ops state)

### 4.4 Provider Health

* `provider_429_total{provider="openai|github|pinecone"}`
* `provider_error_total{provider="openai|github|pinecone"}`
* `provider_request_latency_seconds{provider="..."}`

### 4.5 Cost

* `embedding_tokens_total`
* `llm_tokens_total`
* `budget_utilization_ratio`
* `cache_hit_ratio{cache="embedding|retrieval"}`

### 4.6 Data Growth

* `pinecone_vectors_total`
* `postgres_table_row_count{table="chunks"}`
* `postgres_table_row_count{table="query_logs"}`
* `postgres_query_duration_seconds` (p50/p95/p99)  *(added to support DB slow query triggers)*

---

## 5. Resource Limits (Current MVP Architecture)

### 5.1 Compute

**CPU:** 1 vCPU shared (practical ~80% sustained)  
**Memory:** 2 GB RAM (practical ~1.8GB before OOM risk)  
**Disk:** 60 GB SSD (practical ~54GB before failures)

### 5.2 Default Runtime Settings (Operational Defaults)

These defaults make capacity planning reproducible:

* **Uvicorn workers:** 2
* **Celery concurrency:** 4
* **PostgreSQL shared_buffers:** 128MB default (tune carefully on 2GB)
* **Redis memory cap:** sized to fit within total RAM budget
* **Reranker:** cross-encoder reranking is CPU-bound; under concurrency, reranker is the primary bottleneck on 1 vCPU.

### 5.3 Cache

**Redis:**

* **Memory allocation:** 256 MB (tunable)
* **Eviction policy:** `allkeys-lru`
* **TTL (canonical):**
  * embedding: 24h
  * retrieval: 60s
  * rate limit: 1h sliding window

**Namespace convention (required):**

* `cache:embedding:*`
* `cache:retrieval:*`
* `ratelimit:*`
* `ops:*`

This enables safe partial cache flushing during incidents.

### 5.4 External Service Limits (Operational Reality)

**OpenAI API (Pay-as-you-go):**

* Provider limits vary by account tier.
* Capacity planning monitors **429 rate** and **provider latency** for degradation triggers.

**Pinecone Free Tier (Operational Cap):**

* **Vectors:** 100k max (hard cap)
* **Safe region:** ≤ 80k vectors
* **Performance:** vector search p95 typically 100–300ms; cold access may spike

---

## 6. Capacity Thresholds (Canonical Table)

> **Canonical note:** the “sustained” windows used in this table match the **Scaling Triggers (Section 3)** windows. If there is any mismatch, **Section 3 wins**.

### 6.1 Immediate Action (SEV-1/SEV-2)

| Metric              | Warning (Window)                 | Critical (Window)                | Action                         |
| ------------------- | -------------------------------- | -------------------------------- | ------------------------------ |
| CPU Usage           | > 70% (60m)                      | > 80% (15m)                      | Apply guardrails → upgrade     |
| Memory Usage        | > 80% (15m)                      | > 90% (5m)                       | Apply guardrails → upgrade     |
| Disk Usage          | > 80% (15m)                      | > 90% (5m)                       | Purge/archival → expand        |
| DB Connections      | > 8/10 (15m)                     | = 10/10 (5m) or failures         | Tune pool/queries → RDS        |
| DB Query p95        | > 200ms (30m)                    | > 500ms (15m) or timeouts        | Index/tune → RDS               |
| Query Latency (p95) | > 2.0s (60m)                     | > 2.5s (15m)                     | Guardrails + bottleneck fix    |
| SSE Streams         | > 150 (10m)                      | > 200 (5m)                       | SSE guardrails + scale         |
| Budget Utilization  | > 80% (monthly)                  | = 100% (monthly)                 | Retrieval-only + optimize      |
| Pinecone Vectors    | > 80k (instant)                  | ≥ 100k (instant)                 | Pause ingestion + upgrade      |

### 6.2 Growth Planning (1–3 months)

| Metric           | Early Warning | Planning Trigger | Migration Deadline |
| ---------------- | ------------- | ---------------- | ------------------ |
| Pinecone Vectors | > 50k         | > 70k            | > 80k              |
| Monthly Queries  | > 25k         | > 40k            | > 50k              |
| Concurrent Users | > 50          | > 70             | > 80               |
| Database Size    | > 30 GB       | > 40 GB          | > 50 GB            |

---

## 7. Forecasting

### 7.1 Vector Growth Forecast

Track daily:

* `pinecone_vectors_total`
* `vectors_added_per_day = Δ(vectors_total) / Δ(days)`

Estimate:

* `days_to_80k = (80k - current_vectors) / vectors_added_per_day`
* `days_to_100k = (100k - current_vectors) / vectors_added_per_day`

If `days_to_80k < 30`, begin Pinecone upgrade planning immediately.

### 7.2 Cost Burn Forecast

Track daily:

* `daily_cost_estimate = (embedding_tokens * embed_rate) + (llm_tokens * llm_rate)`
* `days_to_budget_cap = (monthly_cap_remaining / daily_cost_estimate)`

If `days_to_budget_cap < 14`, enforce stricter token budgets and increase caching.

---

## 8. Upgrade Paths

### 8.1 Tier 1 → Tier 2: Enhanced Lightsail

**When:** CPU > 70% sustained OR Memory > 80% sustained OR users > 80 OR queries > 25k/mo  
**Target:** Lightsail 4GB (2 vCPU, 4GB RAM, 80GB SSD)

**Changes:**

* Uvicorn workers: 4
* Celery concurrency: 8 (monitor CPU)
* Postgres shared_buffers: 512MB (tune carefully)
* Redis memory: 512MB
* Off-peak ingestion enforced

### 8.2 Vector Tier Upgrade Path (New, Explicit)

**When to upgrade Pinecone tier:**

* `pinecone_vectors_total > 80k` (planning) OR
* retrieval p95 > 700ms sustained 15m attributable to Pinecone OR
* the system must support **> 100k vectors**.

**Operational steps (high level):**

1. Freeze ingestion scheduling (set `ingestion_paused_state=1`).
2. Upgrade Pinecone tier (Starter/Serverless or equivalent).
3. Validate: upsert enabled, query latency stable, index healthy.
4. Resume ingestion (set `ingestion_paused_state=0`) with ramp-up (25% → 50% → 100%).

### 8.3 Tier 2 → Tier 3: AWS ECS + Managed Services

**When:** users > 200 OR queries > 50k/mo OR need 99.9%+ uptime OR horizontal scaling  
**Target:** ECS (2–4), RDS (Multi-AZ), ElastiCache, ALB

### 8.4 Tier 3 → Tier 4: Enterprise

**When:** users > 1000 OR queries > 500k/mo OR multi-region OR 1M+ chunks  
**Target:** ECS/Fargate, Aurora Serverless v2, Redis cluster, Pinecone Enterprise

---

## 9. Automatic Guardrails (Degraded Mode)

These guardrails keep the service alive and protect p95 latency on small hardware.

### 9.1 Guardrail State Machine

States:

* **NORMAL**
* **DEGRADED-1**
* **DEGRADED-2**
* **RECOVERY**

**Cooldown rule:** 10 minutes between escalations (SEV-1 overrides).  
**State storage (best-effort):** `ops:guardrail_state` in Redis (plus persisted log line per transition).  
**Durability note:** Redis on the MVP instance is not fully durable. Guardrail state restore is **best-effort** unless transitions are also written to Postgres or a local append-only file.

**Restart behavior:** on full service restart, guardrail state defaults to NORMAL unless restored from best-effort state storage.

**Recovery ordering:** restore features in reverse shedding order (LLM → reranking → SSE → ingestion), and only when CPU/latency are stable.

### 9.2 CPU Guardrails

**Trigger A:** CPU > 80% sustained 5m → DEGRADED-1  
* top_k 20 → 10  
* rerank batch 20 → 10  

**Trigger B:** CPU > 85% sustained 5m → DEGRADED-2  
* disable reranking (vector-only retrieval)

**Recovery:** CPU < 70% sustained 10m → RECOVERY → NORMAL

### 9.3 SSE Guardrails

* max streams per user: 5
* max stream duration: 45s
* response budget: 500 tokens

**Multi-worker note (required):** SSE stream counts and saturation must be **aggregated across all Uvicorn workers**, not measured per-process.

**TTFT failover (hard guardrail):** if `t_llm_ttft_ms > 1500ms` → cancel generation → retrieval-only.  
**Rationale:** protects the end-to-end **2.0s p95** envelope by preventing long provider TTFT from consuming the total latency budget.

If `sse_streams_active > 200`:
* reject new SSE (503)
* allow non-streaming retrieval-only (HTTP 200)

### 9.4 Ingestion Guardrails

If query p95 > 2.0s sustained 10m OR CPU > 80% sustained 10m:
* pause ingestion scheduling
* allow safe completion or checkpoint abort
* resume when CPU < 70% sustained 10m AND query p95 < 2.0s sustained 10m

**Safe abort policy (Celery):**

* **Queued tasks:** revoke immediately.
* **Running tasks:** only revoke at SAFE checkpoints:
  * before Pinecone upsert starts OR after a batch upsert completes
* **Unsafe window:** during an active upsert batch (do not hard-kill; allow batch to finish)

**Idempotency contract (required):**

* Pinecone vector IDs must be deterministic: **vector_id = chunk_id**
* Postgres chunk metadata must be upsert-safe: `INSERT ... ON CONFLICT (chunk_id) DO UPDATE`
* Retries must not create duplicate vectors or duplicate rows.

### 9.5 Memory Guardrails

If memory > 90% sustained 5m:

1. reduce Uvicorn workers or Celery concurrency
2. flush only `cache:*` namespaces (NOT `ratelimit:*`)
3. temporarily reduce TTLs (embedding 24h→6h, retrieval 60s→30s)
4. pause ingestion
5. restart services if required (SEV-1)

### 9.6 Budget Guardrails

If `budget_utilization_ratio >= 1.0`:
* disable LLM generation
* retrieval-only with top-3 snippets
* notify admins

### 9.7 Pinecone Hard Cap Guardrails

* **At 95k vectors:** throttle ingestion (50%) + alert
* **At 100k vectors:**
  * enforce write-block (`ops:pinecone_upserts_enabled=0`)
  * switch ingestion to metadata-only
  * alert admin (SEV-2)
  * require upgrade/reduction before enabling upserts again

**Metadata-only ingestion definition (New, explicit):**

When `ops:pinecone_upserts_enabled=0`:

* Ingestion continues to:
  * fetch sources
  * compute chunk metadata
  * write/update Postgres chunk rows
* Ingestion does **not**:
  * create embeddings
  * upsert vectors
* Required tracking fields (conceptual):
  * `chunks.embedding_status = "pending" | "complete" | "failed"`
  * `chunks.embedding_last_attempt_at`
* Resume procedure after upserts re-enabled:
  1. keep `ingestion_paused_state=1`
  2. run a controlled backlog embed/upsert job for `embedding_status="pending"` in batches
  3. re-enable normal ingestion scheduling once backlog is cleared

---

## 10. Emergency Procedures

### 10.1 CPU (Load Shedding)

1. reduce rate limit 50/hr → 30/hr
2. restrict SSE
3. pause ingestion
4. reduce Celery concurrency
5. alert on-call (SEV-2)

### 10.2 Memory

1. flush only caches (namespace)
2. reduce workers/concurrency
3. terminate long DB queries if needed
4. alert on-call (SEV-1)

### 10.3 Disk

**Triage check order (do this first):**

1. Check filesystem: `df -h`
2. Check Docker usage: `docker system df`
3. Identify largest directories: `du -h -d 1 /var/lib/docker | sort -h` (or equivalent)
4. Check logs directory (Caddy/app logs) and retention
5. Check backups directory and rotation
6. Check Postgres data directory size and table bloat

**Remediation steps:**

1. `docker system prune` (no volumes)
2. only if confirmed safe: `docker system prune -a --volumes`
3. archive backups to S3, delete local copies
4. purge logs/query_logs only if critical
5. alert on-call (SEV-1)

### 10.4 Retention Purge Runbook

* daily off-peak
* purge query_logs > 90 days
* retention SLO: must succeed once per 24h
* alert if failures 2 days in a row (SEV-2)
* alert if purge volume deviates sharply from trend
* if DB size continues growing past 50GB, treat as SEV-1 disk risk

---

## 11. Load Shedding Order

When the system is under stress, shed load in this order:

1. disable ingestion endpoints
2. restrict SSE (fallback to non-streaming retrieval-only)
3. disable reranking (vector-only retrieval)
4. disable LLM generation (budget cap or TTFT failover)
5. return 503 for new queries (last resort)

**Endpoint classification (operational):**

* **Non-critical (disable first):** `/ingest`, `/reindex`, `/admin/*`
* **Critical (protect):** `/query`, `/health`, `/metrics`

---

## 12. Single Point of Failure Note (MVP)

The Tier-1 MVP is a **single-instance** deployment and therefore a **single point of failure**. High availability targets (e.g., 99.9%+) require Tier 3 (ECS + managed services) or higher.

---

## 13. Related Documents

* Requirements — NFR-1.x, NFR-2.x
* Tech Stack — infra specs, cost, upgrade paths
* Operations — runbooks
* Observability — SLOs, metrics, alerting
* Decisions — canonical rules

---

## Version History

| Version | Date       | Changes |
| ------- | ---------- | ------- |
| v1.0    | 2026-03-11 | Initial capacity planning documentation. |
| v1.1    | 2026-03-11 | Separated operational vs architectural limits; added workload assumptions, SSE metrics, forecasting, guardrails. |
| v1.2    | 2026-03-11 | Added baseline measurement conditions; clarified baselines apply to ≤80k vectors; TTFT failover; ingestion pause; safe docker prune; retention purge runbook. |
| v1.3    | 2026-03-11 | Added window definitions; guardrail state machine; safe abort; redis namespace; pinecone hard-cap guardrails; endpoint shedding order; retention escalation. |
| v1.4    | 2026-03-11 | Unified trigger windows across sections; added SEV override rule; clarified DB size vs disk coupling; required guardrail state persistence; added pinecone write-block enforcement key; added ingestion pause state metric. |
| v1.5    | 2026-03-11 | Clarified guardrails vs scaling triggers; added restart behavior for guardrail state; added recovery ordering; added TTFT threshold rationale tied to p95 envelope; added explicit idempotency contract (Pinecone + Postgres upserts); added endpoint classification; documented MVP single point of failure. |
| v1.6    | 2026-03-11 | Fixed sustained-window ambiguity by making Section 6 reference Section 3 (Section 3 wins); added explicit DB slow-query triggers and metric usage; added disk triage check order before prune; clarified guardrail state persistence as best-effort on Redis; added SSE multi-worker aggregation note; clarified TTFT soft budget vs hard guardrail; defined metadata-only ingestion behavior and backlog resume procedure; added explicit vector tier upgrade path. |