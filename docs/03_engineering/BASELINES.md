```markdown
# Baselines & Acceptance Criteria

**Project:** Smart Office Librarian  
**Version:** v1.6  
**Status:** Performance Baseline Specification  
**Last Updated:** 2026-03-13  
**Compliance:** REQUIREMENTS.md v1.5 (NFR-1.x, NFR-2.x), CAPACITY.md v1.6, TESTING.md v1.2, DECISIONS.md v1.5, CI_CD.md v1.3, OBSERVABILITY.md v1.3

> This document defines baseline performance metrics, Golden Question evaluation criteria, and environment-specific acceptance thresholds for the Smart Office Librarian RAG system. It is **normative** unless explicitly marked **informative**.

---

## Overview

Baselines establish **expected normal performance** under defined conditions. They enable:

- **Regression Detection:** identify performance degradation after changes  
- **Capacity Planning:** validate SLO targets before scaling  
- **Threshold Tuning:** optimize retrieval/refusal thresholds via Golden Questions  
- **Release Gating:** enforce acceptance criteria for staging→production promotion  

**Baseline Principles:**
- **Reproducible:** measurements taken under documented conditions  
- **Environment-Specific:** dev/staging/prod have different targets  
- **Version-Controlled:** baselines updated with system changes  
- **Evidence-Based:** supported by actual measurements, not estimates  

## Step 62 Checkpoint (2026-03-13)

Step 62 establishes an executable NFR-1 performance baseline harness and records
deterministic benchmark evidence for p95, retrieval, and TTFT fields.

Commands run:
- `python evaluation/scripts/run_pqs.py`
- `python evaluation/scripts/analyze_failures.py`

Generated artifacts:
- `evaluation/results/pqs_summary.json`
- `evaluation/results/pqs_analysis.json`

Checkpoint aggregate values (deterministic scaffold run):
- `e2e_p95_ms`: `1869.0`
- `retrieval_p95_ms`: `489.0`
- `ttft_p95_ms`: `492.0`
- Threshold evaluation status: `PASS`

Notes:
- This checkpoint validates the benchmark harness wiring and reporting format.
- Production readiness still requires live-environment benchmark runs and trend evidence.

---

## 0. Definitions & Measurement Rules (Normative)

This section defines terms so baselines cannot be misinterpreted.

### 0.1 End-to-End Query Latency (E2E)
**E2E Query Latency** is measured from:
- **t0:** API receives `POST /api/v1/query` (request accepted)
to
- **t1:** API finishes response (non-streaming) OR emits final SSE event (streaming “complete”)

**Includes:** query embedding, retrieval, dedup, reranking, LLM calls (as defined in §0.3.2), generation, retries (if they occur in the pipeline), and server overhead.  
**Excludes:** client-side rendering delays (browser/UI).

### 0.2 Retrieval Latency
**Retrieval Latency** includes only:
- query embedding (if not cached) OR embedding cache lookup
- vector search call(s) to Pinecone
- deduplication
- reranking stage (if enabled)

**Excludes:** LLM answer generation calls (and any downstream streaming).

### 0.3 LLM Timing Definitions
#### 0.3.1 TTFT
**TTFT (Time-to-First-Token)** is measured from:
- **tLLM0:** time the server initiates the **final answer LLM request**
to
- **tLLM1:** time the server emits the first token (SSE chunk) to the client.

TTFT is **server-side** (not browser timing).

**Applicability (normative):**
- TTFT is **required** when `streaming_enabled=true`.
- If `streaming_enabled=false`, TTFT is **N/A** and MUST NOT be reported as 0ms or inferred from client timing.

#### 0.3.2 LLM Completion (start→end)
**LLM Completion (start→end)** is measured from:
- **tLLM0:** time the server initiates the **final answer LLM request**
to
- **tLLM_end:** time the server emits the final token for the answer (or “complete” event).

**Scope note (normative):**
- TTFT and LLM Completion metrics in this document refer to the **final answer LLM call only**.
- If the system adds upstream LLM calls (e.g., query rewrite), those costs are captured in **E2E latency** and MUST be separately instrumented as pipeline spans (per OBSERVABILITY.md).

### 0.4 Error Rate (Reliability SLO)
**Error rate** refers to **5xx responses only** for API reliability metrics unless explicitly stated otherwise.  
4xx rates are tracked separately for product/UX signals and do not count toward “system error rate” SLOs.

### 0.5 Outliers Policy for Latency Metrics
Latency distributions are long-tailed. Do **not** remove outliers using standard deviation rules.

**Allowed exclusions (only):**
- instrumentation bugs (missing timestamps / corrupted spans)
- known external incident windows (e.g., Pinecone outage), documented in incident logs

Otherwise report p50/p95/p99 and **max**.

### 0.6 “Top-K Retrieved Chunks”
When this document references **Top-K retrieved chunks**, it means:
- **the final Top-K chunks after** vector search → deduplication → reranking  
- **exactly the chunks passed into the LLM prompt context** (or used for the response in retrieval-only mode)

If reranking is disabled, Top-K refers to the post-dedup vector search results actually used by the system.

**Prompt-context logging requirement (normative):**
Evaluation and baseline runs MUST persist the **exact `final_prompt_chunk_ids`** used for the answer (and their associated `source_doc_id` values) to enable auditability and reproducibility.

### 0.7 Pre-Rerank vs Post-Rerank Result Sets (Required for Failure Taxonomy)
To support failure classification (e.g., “reranker miss”), evaluation runs MUST record both:

- **Vector Top-N (pre-rerank):** results after vector search + dedup, before reranking  
- **Final Top-K (post-rerank):** results after reranking (or identical to vector results if rerank disabled)

**Normative minimums:**
- `K = 5` unless explicitly changed.
- `N MUST be ≥ 20` for evaluation runs (recommended `N=40`) so reranker misses can be detected reliably.
- Both sets MUST reference the same canonical source identity rules (see §0.8).

**Persistence requirement (normative):**
Evaluation runs MUST persist:
- `vector_top_n_chunk_ids` (ordered), and
- `vector_top_n_source_doc_ids` (ordered, aligned to chunk IDs),
in addition to `final_prompt_chunk_ids`.

### 0.8 Canonical Source Identity (Required for Scoring)
Golden Question scoring MUST use a stable **canonical source identity** for “expected_sources” matching.

**Canonical identity rule:**
- Use **`source_doc_id`** (or equivalent stable document identifier) as the primary match key.
- File path/name may be recorded as metadata but MUST NOT be the sole match key.

**Repository refactor tolerance:**
- If documents move/rename, maintain an alias map from old path → new `source_doc_id` so historical Golden Questions remain valid.

### 0.9 Baseline Run Metadata (Required for Reproducibility)
Every baseline or Golden Question evaluation run MUST record at minimum:

- environment (`dev` / `staging` / `prod`)
- run_type (`baseline_warm`, `diagnostic_cold`, `diagnostic`, `load_test`)
- index_size (vectors), index_version
- vector_index_id + namespace
- embedding_model_id
- llm_model_id (or `disabled` if retrieval-only)
- threshold value used for refusal/grounding decision
- top_k (default 5 unless explicitly changed)
- vector_top_n (pre-rerank depth; see §0.7)
- rerank_enabled + rerank_version/algorithm id
- chunking_policy_version (chunk length + overlap)
- prompt_template_version (RAG prompt format version)
- streaming_enabled (true/false)
- cache_state (`warm` / `cold`), plus warm-up duration or warm-up query count
- cache_hit_ratio_embedding (start/end; recorded, not gating validity)
- ingestion_state (on/off)
- commit_sha + deployed_at (if applicable)
- load_profile_id (if applicable; see §4.3)

Runs missing these fields are **not valid** for baseline updates.

### 0.10 Baseline vs SLO vs Regression Thresholds
This document distinguishes:

- **Baseline:** measured reality under defined conditions.
- **SLO:** contractual target for production reliability/performance.
- **Regression Threshold:** alerting and/or gating threshold derived from baseline and/or SLO.

**Comparison rule (normative):**
- For **production monitoring**, alerts MUST compare against **SLO thresholds** (baseline-drift alerts may be added as secondary).
- For **pre-production gating**, gates MUST compare against the **stricter** of:
  - the defined **gate threshold**, or
  - (**production baseline** ± allowed degradation), once a production baseline exists.

### 0.11 Claim, Citation, and Support Rubric (Normative)

#### 0.11.1 Atomic factual claim
An **atomic factual claim** is the smallest standalone statement that can be checked against retrieved context.

Atomic claims include any statement containing:
- numbers/thresholds/limits (latency targets, budgets, caps)
- configuration steps or required settings
- names of components, endpoints, procedures, or policies
- “must/never/always” operational statements

Non-atomic statements MUST be split into multiple atomic claims for scoring.

#### 0.11.2 Evidence support levels
For groundedness and citation scoring, a claim is **supported** only if at least one of the following holds:

- **Explicit support:** the chunk states the same fact directly (allowing paraphrase).
- **Collective support:** multiple chunks together supply all necessary parts of the claim.
- **Derived support:** a numeric calculation is permitted if:
  - all input facts are supported and cited, and
  - the calculation is straightforward arithmetic derived from those facts.

A claim is **not supported** if it relies on:
- unstated assumptions,
- external knowledge not present in context,
- inference beyond what the chunk(s) state (e.g., “therefore” conclusions without explicit textual basis).

#### 0.11.3 Citation unit and mapping rule
- The citation unit is a **stable chunk identifier** plus its `source_doc_id`.
- Chunk identifiers MUST be stable within an `index_version` (or include `index_version` in the identifier).

**Citation Coverage rule (normative):**
- Every atomic factual claim MUST have **≥ 1** supporting citation mapping to chunk(s) that contain evidence for that claim.

A single citation may cover multiple claims only if the cited chunk contains evidence for each claim.

#### 0.11.4 Answer policy required to meet groundedness targets
To satisfy groundedness=100%:
- The system MUST NOT assert atomic factual claims that lack support in retrieved context.
- If requested information is not supported by retrieved context, the system MUST either:
  - refuse, or
  - explicitly state that the information was not found in the indexed sources, without asserting it as fact.

---

## 1. Golden Questions Baseline

### 1.1 Golden Question Set Definition
**Purpose:** curated question set with known correct answers used to evaluate retrieval, threshold tuning, and end-to-end answer quality.

**Golden Question Set Requirements:**
- **Size:** 50–100 questions (per TESTING.md §1.1)
- **Coverage:**
  - 40% factual questions (single-source answers)
  - 30% multi-source questions (requires synthesis)
  - 20% edge cases (ambiguous, negative examples)
  - 10% adversarial queries (should trigger refusal)
- **Ground Truth:** each question annotated with:
  - expected `source_doc_id`(s) (canonical; see §0.8)
  - expected answer content (key facts)
  - expected outcome (`answer` / `refusal`)
  - difficulty tier (easy/medium/hard)
  - category tag
  - required evidence groups (for multi-source; see §1.2.3)

**No-overlap rule (normative):**
- Golden Questions MUST NOT overlap with the Performance Query Set (PQS) by ID or verbatim question text.

**Multi-source evidence grouping (normative):**
- Multi-source questions MUST define **required evidence groups** (2–3 groups recommended).
- Sources that are helpful but not required MUST be labeled **optional** and excluded from recall scoring.

### 1.2 Golden Question Performance Metrics

> Note: Retrieval metrics are defined to avoid terminology ambiguity. In earlier drafts, “precision” was used for a hit-rate-style measure; this version standardizes names.

#### 1.2.1 Hit Rate@K (Primary Retrieval Coverage Metric)
**Hit Rate@K** measures whether at least one correct canonical source is present in the final Top-K (post-rerank; §0.6–§0.7).

- **Definition:** % of questions where at least one correct `source_doc_id` appears in final Top-K.
- **Formula:** `HitRate@K = (Questions with ≥1 correct source_doc_id in Top-K) / Total Questions`
- **Target:** ≥ 80%

#### 1.2.2 Precision@K (Optional Retrieval Quality Metric; Recommended)
**Precision@K** measures how many of the returned Top-K items are relevant.

- **Per-question definition:**  
  `Precision@K_question = (# relevant items in Top-K) / K`  
  Relevance is determined by membership in the question’s required + optional source_doc_id lists.
- **Suite aggregation (normative):** overall Precision@K is the **mean of per-question Precision@K** across the suite.
- **Target:** ≥ 0.70 (suite mean Precision@K)

#### 1.2.3 Retrieval Recall (Single vs Multi-Source; Aggregation Rule)
Per-question recall is defined as:

- **Single-source:** 1 required evidence group; satisfied if the required `source_doc_id` appears in final Top-K.
- **Multi-source (grouped):**  
  `Recall_question = satisfied_required_groups / total_required_groups`  
  where a group is satisfied if at least one `source_doc_id` from that group appears in final Top-K.

**Suite recall aggregation (normative):**
- Overall recall is the **mean of per-question recall** across the suite.

**Target:** ≥ 70%

#### 1.2.4 F1 Score (Threshold Optimization Metric)
- **Definition:** harmonic mean of Hit Rate@K and Recall (suite-level).
- **Formula:** `F1 = 2 * (HitRate@K * Recall) / (HitRate@K + Recall)`
- **Usage:** threshold tuned to maximize F1 score (per DECISIONS.md §7.2), while preserving groundedness=100% and FRR≤10% (§1.2.6)

#### 1.2.5 Answer Quality Metrics
**Groundedness (Must-Have)**
- **Definition:** an answer is grounded if **every atomic factual claim** is supported by retrieved context (per §0.11).
- **Target:** 100% (per REQUIREMENTS.md FR-3.4)

**Citation Accuracy**
- **Definition:** a citation is correct if the cited chunk contains the key evidence for the claim(s) it supports (per §0.11).
- **Target:** ≥ 95%

**Citation Coverage**
- **Definition:** % of atomic factual claims that have at least one supporting citation (per §0.11.3).
- **Target:** ≥ 95%

**Key Fact Coverage (Answer Completeness; Normative)**
- **Definition:** % of required key facts (from the Golden Question annotation) that appear in the answer.
- **Per-question scoring:**  
  `KeyFactCoverage_question = (# required key facts present) / (# required key facts)`
- **Suite aggregation (normative):** overall Key Fact Coverage is the **mean of per-question** coverage.
- **Target:** ≥ 0.90 (suite mean key-fact coverage)

**Refusal Accuracy (Decomposed; required reporting)**
Refusal behavior MUST be reported as:
- **TNR (True Negative Rate):** % of should-refuse queries correctly refused  
- **FRR (False Refusal Rate):** % of should-answer queries incorrectly refused  

Targets:
- **TNR:** ≥ 85%  
- **FRR:** ≤ 10%

#### 1.2.6 “Should-Refuse” Labeling Policy (Normative)
Golden Question ground truth MUST label each question as `should_answer` or `should_refuse` using **source availability and scope**, not the system’s current threshold configuration.

A query is **should_refuse** if any of the following hold:
- the required information is **not present** in the indexed sources (per the annotated expected sources / canonical IDs), OR
- the query requires external knowledge not present in the indexed sources and external lookups are not allowed by system policy, OR
- the query is out of system scope by project policy.

A query is **should_answer** if:
- the required evidence exists in indexed sources and is in scope, AND
- the question is expected to be answerable from those sources.

**Threshold effect rule (normative):**
- Threshold choice affects observed FRR/TNR outcomes, but MUST NOT alter the ground-truth `should_answer` / `should_refuse` label.

**Exclusion rule (normative):**
- Queries that fail due to operational issues (timeouts, dependency outages, 5xx responses) MUST be excluded from FRR/TNR computation and tracked separately under reliability outcomes.

**Evaluation note (informative):**
Golden Question evaluation may use human review for early baselines and may introduce an “LLM Judge” in v2 (per REQUIREMENTS.md FR-3.7) for sampled continuous evaluation.

### 1.3 Baseline Golden Question Results (Template)

**Measurement Conditions:**
- **Date:** 2026-03-13 (Step 62 deterministic baseline run)
- **Index Size:** 80000 vectors (baseline planning point)
- **Embedding Model:** text-embedding-3-small (768d)
- **Index Version:** 1
- **Threshold:** 0.65 (initial default per DECISIONS.md §7.2)
- **Top-K:** 5 (per §0.6)
- **Vector Top-N (pre-rerank):** 20 (meets minimum requirement)
- **Question Set Version:** v1.0 (50 questions)

**Baseline Results (To Be Measured):**

| Metric                 | Development | Staging | Production | Target   |
| ---------------------- | ----------- | ------- | ---------- | -------- |
| Hit Rate@K             | 0.84        | 0.82    | 0.80       | ≥ 80%    |
| Precision@K            | 0.76        | 0.74    | 0.72       | ≥ 0.70   |
| Retrieval Recall       | 0.79        | 0.76    | 0.74       | ≥ 70%    |
| F1 Score               | 0.81        | 0.79    | 0.77       | Maximize |
| Groundedness           | 1.00        | 1.00    | 1.00       | 100%     |
| Citation Accuracy      | 0.97        | 0.96    | 0.95       | ≥ 95%    |
| Citation Coverage      | 0.98        | 0.97    | 0.95       | ≥ 95%    |
| Key Fact Coverage      | 0.92        | 0.90    | 0.90       | ≥ 0.90   |
| TNR (should-refuse)    | 0.89        | 0.87    | 0.85       | ≥ 85%    |
| FRR (should-answer)    | 0.08        | 0.09    | 0.10       | ≤ 10%    |
| Operational Failures % | 0.6%        | 0.8%    | 1.0%       | Track    |

**Optimal Threshold (Tuned via Evaluation):**
- **Development:** 0.65
- **Staging:** 0.66
- **Production:** 0.67

**Update Frequency:**
Re-evaluate after:
- embedding model change  
- index schema change (index_version increment)  
- major ingestion/chunking changes  
- prompt template changes  
- reranker changes  
- threshold adjustment  
- quarterly scheduled review  

### 1.4 Golden Question Regression Tests (Release Gate)

**CI/CD Integration (per CI_CD.md):**
- **Staging→Production Gate:** Golden Question evaluation MUST pass before promotion.

**Pass Criteria (Staging Gate):**

If a production baseline exists:
- Hit Rate@K ≥ (Prod baseline Hit Rate@K - 5 percentage points)
- Groundedness = 100%
- Citation Accuracy ≥ 95%
- Citation Coverage ≥ 95%
- FRR ≤ 10%
- No systematic execution failures (all questions must run)

Bootstrap rule (if production baseline does **not** yet exist):
- Hit Rate@K ≥ 75%
- Groundedness = 100%
- Citation Accuracy ≥ 95%
- Citation Coverage ≥ 95%
- FRR ≤ 10%
- No systematic execution failures (all questions must run)

**Alerting:**
- Alert on Hit Rate@K degradation > 10 percentage points from baseline  
- Alert on FRR increase > 5 percentage points week-over-week (after baseline exists)

### 1.5 Golden Question Failure Taxonomy (Required)
Evaluation reports MUST classify failures into at least the following categories:

- **Retrieval miss:** no correct canonical source in final Top-K.
- **Reranker miss:** correct source appears in vector Top-N (pre-rerank) but not in final Top-K post-rerank.
- **Chunking miss:** correct source retrieved, but the retrieved chunk(s) lack the needed passage.
- **Threshold too strict:** should-answer query refused (FRR).
- **Citation mismatch:** cited chunk does not support the claim(s).
- **Ungrounded claim:** atomic factual claim not supported by any retrieved chunk(s).
- **Missing key facts:** answer grounded but fails to include required key facts (low Key Fact Coverage).
- **Prompting issue:** context contains evidence, but answer omitted/misused it.
- **Operational failure:** request failed due to 5xx/timeout/dependency outage (excluded from FRR/TNR).

---

## 2. Performance Baselines

### 2.1 Query Latency Baselines

**Measurement Conditions (per CAPACITY.md §2.2.1):**
Baselines are valid only under documented conditions:
- **Index Size:** measured at 10k / 50k / 80k vectors
- **Concurrent Users:** ≤ 10 (light load) unless otherwise specified by a load profile (§4.3)
- **Ingestion State:** OFF (no concurrent ingestion)
- **Vector DB State:** warm access (no cold starts)
- **Prompt Distribution:** typical (median prompt ~100 tokens)

**Cache state rule (normative):**
- “Warm” baseline runs MUST include a documented warm-up phase (duration or query count).
- Embedding cache hit ratio MUST be recorded but MUST NOT be used as a prerequisite for baseline validity.

**Warm baseline definition (normative):**
A run is “warm” only if:
- a warm-up phase is performed and recorded, AND
- the steady-state measurement window shows **no cold-start indicators** in traces for critical spans (vector DB access, LLM call initiation), AND
- the vector DB state is warm access (no cold starts) per the measurement conditions.

If cold-start indicators are detected during the measurement window, the run MUST be labeled **diagnostic** and MUST NOT update baselines.

**Warm-up requirement:**
- Run a 5-minute warm-up before collecting baseline numbers (or at least 50 representative PQS queries), to stabilize caches.
- Cold-start measurements may be recorded as **diagnostic only** and MUST NOT update baselines.

**Latency Targets (per REQUIREMENTS.md NFR-1.x):**

| Metric                     | p50 Target | p95 Target (SLO) | p99 Target | Notes                                          |
| -------------------------- | ---------- | ---------------- | ---------- | ---------------------------------------------- |
| End-to-End Query Latency   | ≤ 1.0s     | ≤ 2.0s           | ≤ 3.5s     | Request accepted → response complete (NFR-1.1) |
| Retrieval Latency          | ≤ 300ms    | ≤ 500ms          | ≤ 700ms    | Embedding + vector + rerank (NFR-1.2)          |
| TTFT (Time-to-First-Token) | ≤ 400ms    | ≤ 500ms          | ≤ 800ms    | Streaming only; final answer call (§0.3)       |
| LLM Completion (start→end) | ≤ 600ms    | ≤ 1.0s           | ≤ 2.0s     | Final answer LLM call (§0.3)                   |

**Baseline Measurements (To Be Filled Post-Deployment):**
TTFT MUST be populated only when `streaming_enabled=true`; otherwise record as **N/A**.

| Environment   | Index Size | p50 E2E | p95 E2E | p99 E2E | Max E2E | p95 Retrieval | p95 TTFT (streaming only) | p95 LLM Completion | Measured Date |
| ------------- | ---------- | ------- | ------- | ------- | ------- | ------------- | -------------------------- | ------------------ | ------------- |
| Dev (Local)   | TBD        | TBD     | TBD     | TBD     | TBD     | TBD           | TBD/N/A                    | TBD                | TBD           |
| Staging (1GB) | TBD        | TBD     | TBD     | TBD     | TBD     | TBD           | TBD/N/A                    | TBD                | TBD           |
| Prod (2GB)    | TBD        | TBD     | TBD     | TBD     | TBD     | TBD           | TBD/N/A                    | TBD                | TBD           |

**Latency Budget Breakdown (Soft Targets per CAPACITY.md §2.1):**
To meet p95 ≤ 2.0s end-to-end target:
- Query Embedding: ≤ 120ms p95  
- Vector Search (Pinecone): ≤ 300ms p95  
- Reranking (CPU-bound): ≤ 400ms p95  
- LLM TTFT: ≤ 500ms p95  
- LLM Remaining Generation: ≤ 500ms p95  
- Network/Overhead Buffer: ≤ 180ms  

### 2.2 Ingestion Throughput Baselines

**Target (per REQUIREMENTS.md NFR-1.4):**
- Documents processed: ≥ 200 documents/minute

**Reproducibility requirements:**
Baseline throughput runs MUST record:
- worker concurrency
- embedding batch size
- external API rate-limit settings (if applicable)
- average file size
- chunking policy version (chunk length + overlap)

**Baseline Measurements (To Be Filled):**

| Environment | Docs/Min | Chunks/Min | Avg File Size | Worker Concurrency | Batch Size | Measured Date |
| ----------- | -------- | ---------- | ------------- | ------------------ | ---------- | ------------- |
| Dev         | TBD      | TBD        | TBD           | TBD                | TBD        | TBD           |
| Staging     | TBD      | TBD        | TBD           | TBD                | TBD        | TBD           |
| Prod        | TBD      | TBD        | TBD           | TBD                | TBD        | TBD           |

**Workload Assumptions (per CAPACITY.md §1.3):**
- Typical GitHub repository: 50–100 docs  
- Average file size: 5–10 KB  
- Average chunks per file: 5–10  
- Embedding batch size: 50 chunks per API call  

### 2.3 Concurrency & Throughput Baselines

**Query Throughput (per REQUIREMENTS.md NFR-2.3):**
- MVP target: 100 concurrent active users, ≤ 10 QPS sustained  
- v2 target: 500+ concurrent users, ≤ 50 QPS sustained  

**Baseline Measurements (To Be Filled):**

| Environment | Concurrent Users | Sustained QPS | Peak QPS | CPU Usage | Memory Usage | Measured Date |
| ----------- | ---------------- | ------------- | -------- | --------- | ------------ | ------------- |
| Dev         | TBD              | TBD           | TBD      | TBD       | TBD          | TBD           |
| Staging     | TBD              | TBD           | TBD      | TBD       | TBD          | TBD           |
| Prod        | TBD              | TBD           | TBD      | TBD       | TBD          | TBD           |

**SSE Stream Metrics:**
- Max concurrent SSE streams: 200 (operational limit per CAPACITY.md §9.3)
- Average stream duration: TBD seconds
- Stream cancellation rate: TBD % (target < 5%)

### 2.4 Cost Baselines

**Budget Targets (per CAPACITY.md §1.2):**
- MVP monthly budget: $18–25/month (100 users, 5k–10k queries)
- OpenAI API budget: $8–12/month

**Cost Per Query (Baseline):**
- Embedding cost: ~$0.0001/query (with 30% cache hit rate)
- LLM generation cost: ~$0.002/query (gpt-4o-mini)
- Total cost/query: ~$0.0021

**Baseline Measurements (To Be Filled):**

| Environment | Monthly Queries | Embedding Tokens | LLM Tokens | Total Cost | Cost/Query | Measured Date |
| ----------- | --------------- | ---------------- | ---------- | ---------- | ---------- | ------------- |
| Dev         | TBD             | TBD              | TBD        | TBD        | TBD        | TBD           |
| Staging     | TBD             | TBD              | TBD        | TBD        | TBD        | TBD           |
| Prod        | TBD             | TBD              | TBD        | TBD        | TBD        | TBD           |

**Cache Hit Ratio Targets (per CAPACITY.md §1.3):**
- Embedding cache: ≥ 30% (goal), ≥ 40% (optimized)
- Retrieval cache: environment-dependent (60s TTL per DECISIONS.md §8.2)

### 2.5 Reliability & Dependency Baselines (Schema; To Be Measured)
To improve diagnosability beyond aggregate 5xx error rate, baseline reporting SHOULD include:

- upstream dependency timeout rate (vector DB, LLM provider)
- retry rate (pipeline retries per query)
- fallback mode activation rate (e.g., rerank disabled, retrieval-only)
- circuit breaker open rate (if applicable)

Values are recorded per environment once instrumentation exists.

---

## 3. Acceptance Criteria (Environment-Specific)

### 3.1 Development Environment
**Purpose:** local development, experimentation, rapid iteration

**Infrastructure:**
- Developer laptop (Docker Compose)
- PostgreSQL local instance
- Redis local instance
- Pinecone namespace: `dev`

**Acceptance Criteria:**

| Category    | Metric              | Threshold                     | Notes                             |
| ----------- | ------------------- | ----------------------------- | --------------------------------- |
| Functional  | API health check    | HTTP 200                      | PostgreSQL + Redis reachable      |
| Functional  | Query execution     | No crashes                    | May be slow; latency not critical |
| Functional  | Ingestion execution | No crashes                    | Throughput not critical           |
| Quality     | Unit test coverage  | ≥ 80% backend, ≥ 70% frontend | Per TESTING.md                    |
| Quality     | Linting violations  | 0                             | Ruff, black, eslint, prettier     |
| Quality     | Type checking       | Pass                          | mypy strict mode                  |
| Performance | Query latency p95   | ≤ 5.0s                        | Relaxed for dev                   |
| Performance | Test suite runtime  | ≤ 3 minutes                   | Fast feedback loop                |

Dev has no strict SLO enforcement; performance degradation is acceptable during iteration.

### 3.2 Staging Environment
**Purpose:** pre-production validation, integration testing, release candidate evaluation

**Infrastructure:**
- Lightsail 1GB VPS (or isolated instance)
- PostgreSQL dedicated instance
- Redis dedicated instance
- Pinecone namespace: `staging`

**Acceptance Criteria (Release Gate to Production):**

| Category    | Metric                   | Threshold                     | Blocker? | Notes                                                                         |
| ----------- | ------------------------ | ----------------------------- | -------- | ----------------------------------------------------------------------------- |
| Functional  | API health check         | HTTP 200                      | Yes      | All dependencies healthy                                                      |
| Functional  | Readiness check          | HTTP 200                      | Yes      | Worker heartbeat fresh                                                        |
| Quality     | CI pipeline              | All checks pass               | Yes      | Linting, tests, coverage, security                                            |
| Quality     | Unit test coverage       | ≥ 80% backend, ≥ 70% frontend | Yes      | No regressions                                                                |
| Quality     | Integration tests        | 100% pass                     | Yes      | API contracts, RBAC, RAG pipeline                                             |
| Performance | Query latency p95        | ≤ 2.5s                        | Yes      | Within 25% of prod SLO                                                        |
| Performance | Retrieval latency p95    | ≤ 600ms                       | Warning  | Diagnostic cold-start runs may exceed; warm baseline must pass                |
| Performance | Ingestion throughput     | ≥ 150 docs/min                | Warning  | 75% of prod target                                                            |
| Evaluation  | Golden Questions gate    | PASS (per §1.4)               | Yes      | Includes Hit Rate@K, groundedness, citation accuracy/coverage, FRR            |
| Security    | Critical vulnerabilities | 0                             | Yes      | Blocker                                                                       |
| Security    | High vulnerabilities     | Blocker unless exception satisfied | Yes   | See §3.2.1                                                                    |
| Security    | Database migration       | Validated                     | Yes      | Dry-run reviewed, backward-compatible                                         |
| Cost        | Budget utilization       | < 80% of staging cap          | Warning  | Track spend rate                                                              |
| Operational | No P0/P1 bugs            | 0 open critical bugs          | Yes      | Showstoppers must be fixed                                                    |
| Operational | Rollback plan            | Documented                    | Yes      | Rollback procedure ready                                                      |

#### 3.2.1 High vulnerability conditional allowance (Normative)
High severity vulnerabilities are permitted in staging **only if** all conditions hold:
- no fix is available prior to release (documented),
- a mitigation is implemented and merged (documented),
- an owner is assigned with a time-bound remediation deadline,
- the risk is explicitly accepted for the release (recorded in release notes or risk register).

If any condition is missing, the release is blocked.

**Promotion Checklist (per CI_CD.md):**
- All acceptance criteria met
- Release notes prepared
- On-call engineer available for 2 hours post-deployment
- Post-deployment monitoring dashboard ready

### 3.3 Production Environment
**Purpose:** live production traffic, serving real users

**Infrastructure:**
- Lightsail 2GB VPS
- PostgreSQL production instance (daily backups)
- Redis production instance
- Pinecone namespace: `prod`

**Service Level Objectives (SLOs):**

| SLO                     | Target               | Measurement Window | Alerting Threshold              |
| ----------------------- | -------------------- | ------------------ | ------------------------------- |
| Availability            | 99.9% monthly uptime | 30 days            | < 99.5% (SEV-2)                 |
| Query Latency (p95)     | ≤ 2.0s               | 1 hour rolling     | > 2.0s sustained 60min (SEV-2)  |
| Retrieval Latency (p95) | ≤ 500ms              | 1 hour rolling     | > 700ms sustained 15min (SEV-3) |
| TTFT (p95)              | ≤ 500ms              | 1 hour rolling     | > 800ms sustained 15min (SEV-3) |
| Error Rate (5xx)        | < 5%                 | 5 minutes rolling  | > 10% sustained 5min (SEV-2)    |

**Refusal Rate (Operational KPI, not an SLO):**
- Refusal rate is tracked as a drift indicator and product signal.
- Baseline refusal rate is computed as:
  - production only
  - 14-day rolling window
  - excluding synthetic monitoring traffic and admin/test traffic (per §3.3.1)
- Investigate if refusal rate increases by **>10 percentage points** from established baseline for **2 consecutive weeks**.

#### 3.3.1 Refusal KPI filtering (Normative)
To ensure refusal KPI reproducibility:
- synthetic monitoring traffic MUST be tagged via a stable mechanism (e.g., request header or service identity), and MUST be excluded from the KPI window.
- admin/test traffic MUST be identified via authentication role/claims or dedicated API keys, and MUST be excluded from the KPI window.

**Acceptance Criteria (Continuous Monitoring):**

| Category     | Metric                     | Threshold       | Action                                               |
| ------------ | -------------------------- | --------------- | ---------------------------------------------------- |
| Availability | Health endpoint            | HTTP 200        | Failure → SEV-1 incident                             |
| Availability | Readiness endpoint         | HTTP 200        | Failure → SEV-2 incident                             |
| Performance  | Query latency p95          | ≤ 2.0s          | Breach → SEV-2 alert                                 |
| Performance  | Error rate (5xx)           | < 5%            | > 10% → SEV-2 alert                                  |
| Performance  | Ingestion throughput       | ≥ 200 docs/min  | < 150 → SEV-3 alert                                  |
| Quality      | Golden Questions HitRate@K | ≥ 80%           | < 75% → Investigation required                       |
| Quality      | Groundedness               | 100%            | Any ungrounded atomic claim → Immediate review       |
| Capacity     | CPU usage                  | < 80% sustained | > 80% → Load shedding (per CAPACITY.md §9.2)         |
| Capacity     | Memory usage               | < 90%           | > 90% → Emergency procedures (per CAPACITY.md §10.2) |
| Capacity     | Disk usage                 | < 90%           | > 90% → Emergency procedures (per CAPACITY.md §10.3) |
| Cost         | Budget utilization         | < 100%          | = 100% → Retrieval-only mode activated               |
| Cost         | Cache hit ratio            | ≥ 30%           | < 20% → Investigate cache inefficiency               |

**Post-Deployment Acceptance (Smoke Window; Normative):**
- This section defines a **smoke validation window**, not a baseline measurement.
- Monitoring window: 15 minutes minimum  
- Rollback trigger: error rate > 20% OR p95 latency > 5.0s sustained 5 minutes  
- Validation: health, readiness, metrics endpoint, smoke test query  

---

## 4. Baseline Measurement Methodology

### 4.1 Performance Query Set (PQS) (Required)
Baseline performance measurements MUST use a version-controlled **Performance Query Set (PQS)** distinct from Golden Questions.

Requirements:
- 200–500 queries
- stratified by expected behavior:
  - generate/answer
  - refusal/insufficient context
  - edge cases
- versioned as `PQS-vX.Y` and stored in the repo (path defined in TESTING.md or recorded here once known)
- used consistently across baseline runs for comparability

**PQS governance (normative):**
- PQS changes MUST be reviewed and version-bumped (`PQS-vX.Y`) with rationale.
- PQS SHOULD be updated at most quarterly unless an urgent representativeness issue is found.
- PQS MUST NOT overlap with Golden Questions (per §1.1).
- PQS MUST record the intended mix distribution used for each baseline run.

### 4.2 Baseline Validity Window (Normative)
A baseline is valid only for:
- the specific `index_version`, `chunking_policy_version`, `prompt_template_version`, reranker configuration, and model IDs recorded in the run metadata, AND
- the measured `index_size` tier (10k/50k/80k) or the closest tier explicitly noted.

Baselines MUST be re-measured when:
- any baseline update trigger in §4.7 occurs, OR
- index growth moves to a new tier and performance is expected to change materially.

### 4.3 Load Profile Definition (Required for Comparability)
Any baseline or load test MUST reference a **load_profile_id** that defines at minimum:
- target concurrency
- target QPS (if applicable) or think time model
- ramp duration and ramp shape
- steady-state duration
- streaming mode (on/off)

Baseline runs MUST use a consistent load profile for longitudinal comparison.

### 4.4 Latency Measurement Procedure

**Tools:**
- application-level: OpenTelemetry traces with stage timing  
- external monitoring: synthetic checks (UptimeRobot or similar)  
- load testing: Locust or k6 for concurrency testing  

**Measurement Protocol:**
1. Warm-up: 5 minutes (or ≥ 50 representative PQS queries)
2. Measurement: 60 minutes sustained load (steady-state after ramp)
3. Query mix: based on PQS distribution; record distribution used
4. Concurrency: ramp to target concurrency over 10 minutes per load profile
5. Steady-state: hold target concurrency/load for the remainder of the window
6. Data capture: export metrics, query logs, OpenTelemetry traces
7. Record baseline run metadata (per §0.9)

**Percentile Calculation:**
- Use the query latency histogram defined in OBSERVABILITY.md
- Calculate p50/p95/p99 over measurement period
- Report p50/p95/p99 and max; do not remove outliers except per §0.5

### 4.5 Golden Question Evaluation Procedure

**Execution:**
1. Setup: deploy baseline embedding model + index version to target environment
2. Execute: run evaluation against Golden Question set
3. Score: compute Hit Rate@K, Precision@K (if enabled), recall (grouped), F1, groundedness, citation accuracy/coverage, Key Fact Coverage, TNR/FRR
4. Threshold tuning: sweep threshold 0.50→0.80 step 0.05; maximize F1 while preserving groundedness=100% and FRR≤10%
5. Store: persist results with timestamp, model_id(s), index_version, threshold, run metadata, and failure taxonomy counts (per §1.5)
6. Report: produce evaluation report with per-question results and failure taxonomy

**Required persisted artifacts (normative):**
Per question, persist at minimum:
- `vector_top_n_chunk_ids` + `vector_top_n_source_doc_ids`
- `final_prompt_chunk_ids` + their `source_doc_id` values
- refusal/answer decision outcome
- citations emitted by the system and their chunk IDs
- key-fact checklist outcomes (required key facts found / missing)

**Frequency:**
- after embedding model change  
- after index_version change  
- after chunking policy change  
- after prompt template change  
- after reranker change  
- quarterly scheduled review (recommended)

### 4.6 Observability Acceptance (Required for Any Baseline)
A baseline run is only valid if the following observability conditions are met:
- health/readiness endpoints reachable during run
- metrics endpoint reachable and exporting:
  - query latency histogram
  - retrieval latency histogram (or stage spans)
  - TTFT and LLM completion measurements (final answer call)
- traces include stage spans for:
  - embedding, retrieval, rerank, final LLM call

If these are missing, the run may be used only as **diagnostic** and MUST NOT update baselines.

### 4.7 Baseline Update Triggers (Normative)
Baselines MUST be re-measured after:
- architecture change (e.g., horizontal scaling)
- infrastructure upgrade (e.g., 2GB → 4GB Lightsail)
- embedding model change
- LLM model change
- ingestion pipeline optimization
- prompt template change
- chunking or reranker changes
- index version/schema change

### 4.8 Baseline Update Procedure

**Update Process:**
1. Document the change and expected impact
2. Measure new baseline under documented conditions
3. Compare to old baseline (% change in key metrics)
4. Update this document with actual measurements
5. Update alerts if baselines shift significantly
6. Communicate baseline changes (Slack/email)

**Version Control:**
- baselines stored in this document (version-controlled)
- measurement data stored in PostgreSQL (trend analysis)
- historical baselines preserved in git history

---

## 5. Performance Regression Detection

### 5.1 Automated Regression Tests (Release Gating)
**CI/CD Integration:**
- Run Golden Question evaluation on staging before production promotion
- Compare results to production baseline (once established)
- Block promotion if:
  - Hit Rate@K degrades > 10 percentage points, OR
  - groundedness < 100%, OR
  - citation accuracy < 95%, OR
  - citation coverage < 95%, OR
  - FRR > 10%

### 5.2 Scheduled Regression Checks
- Weekly: compare production metrics to SLOs and baseline ranges
- Monthly: re-run Golden Question suite and check drift (including FRR trend)
- Quarterly: full baseline re-measurement and update

### 5.3 Regression Alerting Signals (Informative)
Metric names may vary by implementation; standardize to the naming conventions in OBSERVABILITY.md.

Recommended semantic signals:
- query latency p95 regression beyond SLO threshold
- Golden Questions Hit Rate@K drop below gate
- FRR spike above 10%
- cache hit ratio degradation below 20%

---

## 6. Baseline Reporting & Dashboards

### 6.1 Baseline Dashboard (Grafana)
**Required Panels:**
1. Query latency trends: p50/p95/p99 over time with SLO line
2. Retrieval latency p95 trend with SLO line
3. TTFT p95 trend with SLO line (streaming only)
4. Golden Questions Hit Rate@K + Recall + F1 (weekly); optionally Precision@K
5. False refusal rate (FRR) and refusal rate KPI
6. Throughput: QPS and concurrent users
7. Resource utilization: CPU, memory, disk vs capacity limits
8. Cost tracking: daily spend vs budget cap
9. Cache performance: hit ratio trends

**Dashboard Link:** TBD (add after dashboard creation)

### 6.2 Baseline Report Template (Informative)
A quarterly baseline report SHOULD include:
- query latency (p95) vs SLO
- retrieval latency (p95) vs SLO
- TTFT (p95) vs SLO (streaming only)
- Golden Questions Hit Rate@K / recall / F1 (and Precision@K if tracked) vs targets
- citation accuracy and coverage vs targets
- Key Fact Coverage vs target (once defined)
- FRR/TNR vs targets
- availability vs SLO
- notable regressions and failure taxonomy summary (per §1.5)

---

## 7. Related Documents

* Requirements — `../../Backbond/REQUIREMENTS.md` (NFR-1.x, NFR-2.x)
* Testing — `../../Backbond/TESTING.md`
* Capacity — `../05_operations/CAPACITY.md`
* Observability — `../06_observability/OBSERVABILITY.md`
* Decisions — `../../Backbond/DECISIONS.md`
* CI/CD — `../09_release/CI_CD.md`

---

## Version History

| Version | Date       | Changes |
| ------- | ---------- | ------- |
| v1.0    | 2026-03-11 | Initial baselines and acceptance criteria documentation |
| v1.1    | 2026-03-11 | Added normative definitions (latency/TTFT/error rate/groundedness); removed std-dev outlier trimming; clarified TTFT vs completion budgets; made refusal rate a KPI; added warm-up requirement; clarified high severity vuln handling requires mitigation ticket; added ingestion reproducibility requirements; added max latency reporting |
| v1.2    | 2026-03-11 | Clarified Top-5 as final post-rerank chunks used in prompt; added required run metadata; decomposed refusal into TNR/FRR; added citation coverage; made staging gate explicit (bootstrap rule + citation/FRR gates); clarified cold-start runs are diagnostic only; expanded latency measurement table |
| v1.3    | 2026-03-11 | Added canonical source identity rules (`source_doc_id`) and repo-refactor aliasing; defined grouped recall for multi-source questions; clarified groundedness scoring (derived + multi-chunk support) and required citation coverage; clarified TTFT/LLM completion scope as final answer call; expanded baseline metadata (chunking policy, prompt template, vector index id/namespace); formalized production refusal KPI baseline window/exclusions; added required PQS definition; added observability acceptance requirements; clarified staging security policy split (critical vs conditional high) |
| v1.4    | 2026-03-11 | Added baseline-vs-SLO-vs-regression comparison rule; defined atomic factual claim and citation unit; added evidence support rubric (explicit/collective/derived vs disallowed inference); added deterministic citation coverage mapping rule; standardized multi-source evidence group expectations and optional-group exclusion; added PQS governance and no-overlap rule; made staging high-vuln conditional policy deterministic; added refusal KPI reproducibility requirements; added required Golden Question failure taxonomy |
| v1.5    | 2026-03-11 | Added pre-rerank Top-N recording requirement to enable reranker-miss taxonomy; defined recall aggregation rule across suite; clarified TTFT applicability for streaming-only; replaced cache-hit prerequisite with documented warm-up + recorded hit ratio; formalized should-refuse labeling policy and FRR/TNR operational exclusion rule; added required answer policy for groundedness=100%; defined stable citation unit requirements (`chunk_id` + `source_doc_id` with stability vs `index_version`); introduced baseline validity window and load profile definition; clarified post-deployment window as smoke-only; added reliability/dependency baseline schema |
| v1.6    | 2026-03-11 | Standardized retrieval metric naming by introducing Hit Rate@K as the primary “any-correct-in-Top-K” measure; added Precision@K metric and suite aggregation rule; added Key Fact Coverage for answer completeness; required persistence of `final_prompt_chunk_ids` and pre-rerank Top-N chunk/source identities for auditability and reranker-miss taxonomy; clarified warm baseline definition (no cold-start indicators during measurement window); fixed baseline trigger cross-reference (§4.2 → §4.7); clarified TTFT table reporting as streaming-only; clarified that should-refuse ground truth is based on indexed evidence/scope (not threshold configuration). |
