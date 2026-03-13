# 🏗️ ARCHITECTURE — Smart Office Librarian

**Version:** v1.6  
**Status:** Architecture Specification  
**Last Updated:** 2026-03-11  
**Compliance:** Requirements v1.5, Tech Stack v1.2, DECISIONS v1.5

> This document defines the **system architecture** with clean separation of concerns, explicit class responsibilities, and traceability to requirements and decisions.

> **Note:** This document contains ONLY architectural structure. Operational concerns (testing, deployment, CI/CD, roadmaps) belong in separate documents (TESTING.md, DEPLOYMENT.md, ROADMAP.md, OPERATIONS.md).

---

## Document Purpose

This architecture serves as the **implementation blueprint** for developers. It:

- Maps requirements → components → classes
- Enforces DECISIONS.md as the canonical source of truth
- Provides testable boundaries and clear responsibilities
- Enables parallel development of modules

**Read this AFTER:** PROJECT_OVERVIEW.md, REQUIREMENTS.md, TECH_STACK.md, DECISIONS.md

---

## Architecture Principles

### 1. Clean Architecture (Layered Separation)

**Layer 1: API Layer (FastAPI Routes)**
- Thin controllers
- Input validation
- SSE streaming

**Layer 2: Domain Layer (Services + Business Logic)**
- QueryService, IngestService, RBACService, CostService, HealthService, EvaluationService, ThresholdService, IndexSafetyServices
- Framework-agnostic

**Layer 3: RAG Pipeline Layer (Retrieval + Generation)**
- Chunking, Embedding, Retrieval, Reranking, LLM
- Implements DECISIONS.md exactly
- **No DB repositories imported directly** (pure pipeline logic)

**Layer 4: Infrastructure Layer (DB, Vector Store, Connectors)**
- Repository pattern for data access
- External API clients

**Key Rule:** Dependencies flow downward. Lower layers never import upper layers.

---

## Architectural Invariants (Hard Rules)

### A. Source + Index Metadata Invariants (Index Lifecycle Contract)

**Index metadata fields (stored on Source):**
- `namespace`: active namespace used for retrieval (free tier swap mechanism)
- `index_name` (optional): active Pinecone index name (paid tier swap mechanism)
- `index_model_id`: embedding model id used during ingestion (e.g., `text-embedding-3-small-v1`)
- `index_version`: schema version for embeddings+chunking+normalization
- `last_indexed_sha`: last commit SHA successfully indexed for that source

**Hard rules:**
1. **Source index metadata MUST be updated only after a successful full ingestion or successful reindex validation.**
2. **Failed/partial ingestion MUST NOT update** `index_model_id`, `index_version`, `namespace`, `index_name`, or `last_indexed_sha`.
3. `Settings.INDEX_VERSION` is the canonical “current schema version” used by the runtime.
4. `index_version` represents the combined schema of:
   - chunking settings (tokens/overlap)
   - normalization rules
   - embedding model id
   - any metadata schema changes that affect retrieval compatibility
5. **Ingestion Commit Atomicity (Required):**
   - Ingestion runs are tracked by an `ingest_run_id` (UUID) stored on chunk metadata rows and on vectors.
   - The worker writes all new chunks/vectors under that `ingest_run_id`.
   - Only after successful completion + validation, the worker performs a single atomic **finalize step**:
     - updates Source `last_indexed_sha` and index metadata, and
     - marks `ingest_run_id` as `finalized`.
   - If ingestion fails, `ingest_run_id` remains unfinalized and **MUST NOT** affect active Source metadata.

---

### B. Threshold Access Invariant (DB stays out of RAG)
1. RAG pipeline stages MUST NOT call PostgreSQL repositories directly.
2. Threshold retrieval is a Domain responsibility via `ThresholdService`.
3. `QueryService` fetches the threshold and passes it into the pipeline.
4. **Threshold comparison MUST use cosine similarity score only** (never reranker score).

---

### C. Caching Invariants

**Embedding cache (required):**
- Key: `sha256(query_text + model_id + index_version)`
- TTL: 24h

**Retrieval caching (enabled per DECISIONS.md 8.2):**
- TTL: 60 seconds (per DECISIONS.md canonical)
- Cache key MUST include:
  - `namespace + repo + index_version + last_indexed_sha`
  - **RBAC scope** (user permissions)
- MUST never share cached results across users if RBAC differs
- Prevents serving stale results after ingestion updates

---

### D. Chunk Metadata Contract (Canonical)

All chunk vectors stored in Pinecone MUST include the following metadata fields and types:

- `repo`: string
- `file_path`: string
- `source_type`: string (`github`, etc.)
- `commit_sha`: string
- `start_line`: int
- `end_line`: int
- `chunk_hash`: string
- `model_id`: string (must equal `Settings.EMBEDDING_MODEL_ID`)
- `index_version`: int (must equal `Settings.INDEX_VERSION`)
- `visibility`: string (`private` | `public`) — **MVP v1**; `shared` with group-based access is a v2 feature
- `allowed_user_ids`: list[string] (required for `private`; empty for `public`)
- `ingest_run_id`: string (UUID) (required; supports atomic finalize)

**RBAC rule (Canonical):**
- Retrieval applies a metadata filter equivalent to:
  - `(visibility == "public") OR (allowed_user_ids $in [current_user.id])`
- MVP default: all chunks are `private` unless explicitly configured.

---

### E. Score Semantics Invariant (Rerank vs Cosine)
1. Retrieval ordering MAY use reranker scores.
2. **Refusal and Confidence MUST use cosine similarity**.
3. The candidate used for refusal/confidence is the **primary candidate** selected after ordering.
4. Therefore, RetrievalStage MUST preserve both:
   - `primary_cosine_score` (cosine score of the primary candidate)
   - `primary_rerank_score` (rerank score of the primary candidate)
5. RefusalStage MUST compare `primary_cosine_score` against `threshold`.

---

### F. Health Heartbeat Invariant (Celery)
1. Celery worker heartbeat MUST be represented as Redis keys:
   - `celery_heartbeat:{worker_name}`
2. Worker updates the key every 30 seconds with TTL=90 seconds.
3. HealthService considers workers healthy if:
   - at least one heartbeat key exists and is fresh (age < 60 seconds).

---

### G. Metrics Endpoint Invariant
- The canonical metrics endpoint is:
  - `GET /metrics`
- The API router MAY proxy `/api/v1/metrics` to `/metrics`, but Prometheus scraping MUST target `/metrics`.

---

## Project Structure (Canonical)

This structure represents a complete, production-ready RAG system with comprehensive monitoring, operational procedures, and deployment automation.

### Structure Design Improvements (v1.6)

**1. Cross-Layer Type Contracts (`backend/app/types/`)**
- **Problem Solved:** Prevents circular imports when multiple layers need shared type definitions
- **Contents:** Strongly typed IDs (ChunkId, SourceDocId), retrieval/generation results, evaluation types, pagination
- **Usage:** Import from `app.types.*` instead of creating dependencies between domain/rag/api layers

**2. Pipeline I/O Contracts (`backend/app/rag/contracts/`)**
- **Problem Solved:** Ensures explicit, versioned contracts between pipeline stages (prevents drift)
- **Contents:** PreRerankResults, PostRerankResults, PromptContext, AnswerDraft, FinalAnswer, CitationMap
- **Usage:** Each RAG stage must conform to explicit input/output contracts for testability and predictability

**3. Evaluation Persistence (`evaluation_result.py` + `evaluation_repo.py`)**
- **Problem Solved:** Enables longitudinal tracking of Golden Question performance over time
- **Contents:** Domain model for EvaluationRun + per-question results + 8-category failure taxonomy
- **Usage:** evaluation_service.py persists results to DB for trend analysis, regression detection, threshold tuning history

**4. Single Evaluation Location (`evaluation/` at root)**
- **Problem Solved:** Prevents duplication between `backend/tests/evaluation/` and root-level evaluation framework
- **Rationale:** Golden Questions are **product acceptance criteria**, not unit tests; belong at project root
- **Scripts:** Call `backend/app/domain/services/evaluation_service.py` for actual execution

```
embedlyzer/
│
├── backend/                           # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry, CORS, middleware, startup/shutdown hooks
│   │   │
│   │   ├── api/                       # API Layer
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # API router aggregation
│   │   │       ├── routes/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── query_routes.py        # POST /api/v1/query (SSE streaming)
│   │   │       │   ├── ingest_routes.py       # POST /api/v1/ingest (admin only)
│   │   │       │   ├── admin_routes.py        # Threshold tuning, source CRUD, user management
│   │   │       │   ├── health_routes.py       # GET /api/v1/health, /api/v1/ready
│   │   │       │   ├── metrics_routes.py      # GET /api/v1/metrics (proxy to /metrics)
│   │   │       │   └── feedback_routes.py     # POST /api/v1/feedback (thumbs up/down)
│   │   │       ├── schemas/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── query.py               # QueryRequest, QueryResponse, RefusalResponse
│   │   │       │   ├── ingest.py              # IngestRequest, IngestStatus, IngestRunResponse
│   │   │       │   ├── auth.py                # TokenData, User, LoginRequest, TokenResponse
│   │   │       │   ├── source.py              # SourceCreate, SourceUpdate, SourceResponse
│   │   │       │   ├── feedback.py            # FeedbackRequest, FeedbackResponse
│   │   │       │   └── common.py              # ErrorResponse, PaginatedResponse, HealthResponse
│   │   │       └── dependencies/
│   │   │           ├── __init__.py
│   │   │           ├── auth.py                # JWT validation, current_user injection
│   │   │           ├── rate_limit.py          # Redis-based rate limiter (50/hour)
│   │   │           └── settings.py            # Settings dependency injection
│   │   │
│   │   ├── core/                      # Cross-Cutting Concerns
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Settings (DECISIONS.md canonical mapping)
│   │   │   ├── logging.py             # Structured JSON logger + secret redaction
│   │   │   ├── security.py            # Token encryption (AES-256), password hashing, JWT
│   │   │   ├── errors.py              # ErrorCatalog (HTTP codes + error messages)
│   │   │   ├── telemetry.py           # OpenTelemetry traces + stage timing
│   │   │   ├── caching.py             # Redis cache wrapper (embedding + retrieval)
│   │   │   ├── metrics.py             # Prometheus registry + /metrics exporter (canonical)
│   │   │   └── middleware.py          # Request ID, correlation, timing middleware
│   │   │
│   │   ├── types/                     # Cross-Layer Type Contracts (Prevents Circular Imports)
│   │   │   ├── __init__.py
│   │   │   ├── ids.py                 # ChunkId, SourceDocId, QueryId, RunId (NewType wrappers)
│   │   │   ├── retrieval.py           # RetrievalResult, PreRerankSet, PostRerankSet
│   │   │   ├── generation.py          # GenerationResult, Citation, ConfidenceLevel (enum)
│   │   │   ├── evaluation.py          # GoldenQuestion, KeyFact, EvalRunResult, FailureTaxonomy
│   │   │   └── pagination.py          # Page[T], PageRequest (generic pagination)
│   │   │
│   │   ├── domain/                    # Domain Layer (Business Logic)
│   │   │   ├── __init__.py
│   │   │   ├── models/                # Domain Entities
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py            # User entity (id, role, claims, allowed_user_ids)
│   │   │   │   ├── source.py          # Source (repo + index metadata contract)
│   │   │   │   ├── chunk.py           # Chunk entity (metadata schema + visibility)
│   │   │   │   ├── query_log.py       # QueryLog (prompt_hash, feedback, latencies, costs)
│   │   │   │   ├── budget_status.py   # BudgetStatus (available|warning|exceeded + utilization)
│   │   │   │   ├── ingest_run.py      # IngestRun (id, status, started_at, finished_at, error)
│   │   │   │   ├── threshold.py       # Threshold entity (namespace, index_version, value)
│   │   │   │   ├── feedback.py        # Feedback entity (query_log_id, rating, comment)
│   │   │   │   └── evaluation_result.py  # EvaluationRun + per-question results (Golden Questions persistence)
│   │   │   └── services/              # Domain Services
│   │   │       ├── __init__.py
│   │   │       ├── query_service.py   # Query orchestration + safety + cost gates + threshold
│   │   │       ├── ingest_service.py  # Ingestion trigger + IngestRun tracking
│   │   │       ├── rbac_service.py    # Permission filter builder (visibility OR allowed_user_ids)
│   │   │       ├── evaluation_service.py  # Golden Question eval + F1 tuning
│   │   │       ├── health_service.py  # 5 concrete health checks + Celery heartbeat
│   │   │       ├── cost_service.py    # Monthly spend caps + retrieval-only mode
│   │   │       ├── index_safety_service.py  # Pre-query model/version validation
│   │   │       ├── threshold_service.py     # Threshold CRUD (DB-backed)
│   │   │       └── feedback_service.py      # Feedback collection + analysis
│   │   │
│   │   ├── rag/                       # RAG Pipeline Layer
│   │   │   ├── __init__.py
│   │   │   ├── contracts/             # Strongly Typed Pipeline I/O (Prevents Contract Drift)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retrieval_contracts.py  # PreRerankResults, PostRerankResults, PromptContext
│   │   │   │   └── generation_contracts.py # AnswerDraft, FinalAnswer, CitationMap
│   │   │   ├── chunking/              # Text Processing Pipeline
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chunker.py         # TokenChunker (512 tokens, 50 overlap)
│   │   │   │   ├── line_mapper.py     # LineMapper (tracks start_line, end_line)
│   │   │   │   ├── normalization.py   # Normalizer (code block awareness)
│   │   │   │   └── simhash.py         # SimHashDedupe (3-bit threshold, ingestion-only)
│   │   │   ├── retrieval/             # Retrieval Engine
│   │   │   │   ├── __init__.py
│   │   │   │   ├── embedder.py        # QueryEmbedder (OpenAI + 24h cache)
│   │   │   │   ├── vector_store.py    # VectorStoreClient (Pinecone wrapper)
│   │   │   │   ├── reranker.py        # CrossEncoderReranker (ms-marco + CPU fallback)
│   │   │   │   └── cache_keys.py      # RetrievalCacheKeyBuilder (reserved)
│   │   │   ├── generation/            # Generation Layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── prompt_builder.py  # PromptBuilder (grounded system prompt)
│   │   │   │   ├── answer_generator.py  # AnswerGenerator (gpt-4o-mini + SSE + fallback)
│   │   │   │   ├── citation_mapper.py   # CitationMapper (Source N → metadata)
│   │   │   │   └── confidence_calculator.py  # ConfidenceCalculator (High/Medium/Low)
│   │   │   ├── stages/                # RAG Pipeline Stages
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retrieval_stage.py   # Embedding → vector → rerank → ordering
│   │   │   │   ├── refusal_stage.py     # Threshold refusal (cosine) + top sources
│   │   │   │   └── generation_stage.py  # Budgeting → LLM → citations → confidence
│   │   │   └── pipeline.py            # RAGPipeline (thin orchestrator)
│   │   │
│   │   ├── connectors/                # External Data Sources
│   │   │   ├── __init__.py
│   │   │   ├── base_connector.py      # BaseConnector interface (v2 multi-source)
│   │   │   └── github/
│   │   │       ├── __init__.py
│   │   │       ├── client.py          # GitHubClient (API wrapper + auth)
│   │   │       ├── diff_scanner.py    # GitDiffScanner (commit SHA diff)
│   │   │       ├── extractor.py       # GitHubExtractor (file text extraction)
│   │   │       ├── ignore_rules.py    # IgnoreRules (.librarianignore parser)
│   │   │       └── validators.py      # FileSizeValidator (1MB limit)
│   │   │
│   │   ├── workers/                   # Celery Background Workers
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py          # Celery app config + broker/backend
│   │   │   ├── retry_policy.py        # RetryPolicy (3 retries + exp backoff + jitter)
│   │   │   └── tasks/
│   │   │       ├── __init__.py
│   │   │       ├── ingest_tasks.py    # IngestJobTask (atomic finalize with ingest_run_id)
│   │   │       ├── purge_tasks.py     # PurgeJobTask (delete vectors + metadata)
│   │   │       ├── reindex_tasks.py   # ReindexJobTask (blue-green strategy)
│   │   │       ├── backup_tasks.py    # BackupJobTask (PostgreSQL → S3, 7-day retention)
│   │   │       └── heartbeat_tasks.py # HeartbeatTask (celery_heartbeat:{worker_name}, 30s)
│   │   │
│   │   └── db/                        # Persistence Layer
│   │       ├── __init__.py
│   │       ├── base.py                # SQLAlchemy Base class
│   │       ├── session.py             # Session factory + async session support
│   │       ├── models.py              # ORM models (User, Source, Chunk, QueryLog, Threshold, IngestRun, Feedback, EvaluationRun, EvaluationResult)
│   │       ├── repositories/          # Repository Pattern (data access)
│   │       │   ├── __init__.py
│   │       │   ├── base_repo.py       # BaseRepository (common CRUD operations)
│   │       │   ├── users_repo.py      # UsersRepository (user CRUD + auth lookup)
│   │       │   ├── sources_repo.py    # SourcesRepository (index metadata + last_indexed_sha)
│   │       │   ├── chunks_repo.py     # ChunksRepository (chunk CRUD + batch ops + ingest_run_id)
│   │       │   ├── query_logs_repo.py # QueryLogsRepository (prompt_hash + analytics)
│   │       │   ├── thresholds_repo.py # ThresholdsRepository (per-env tuning)
│   │       │   ├── ingest_runs_repo.py  # IngestRunsRepository (run tracking + finalize)
│   │       │   ├── feedback_repo.py   # FeedbackRepository (user feedback storage)
│   │       │   └── evaluation_repo.py # EvaluationRepository (Golden Question runs + per-question results + taxonomy)
│   │       └── migrations/            # Alembic Database Migrations
│   │           ├── alembic.ini
│   │           ├── env.py
│   │           ├── script.py.mako
│   │           └── versions/
│   │               └── *.py           # Migration scripts (timestamped)
│   │
│   ├── tests/                         # Test Suite
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures (DB, Redis, mocks)
│   │   ├── unit/                      # Unit tests (>80% coverage required)
│   │   │   ├── __init__.py
│   │   │   ├── test_api/
│   │   │   ├── test_domain/
│   │   │   ├── test_rag/
│   │   │   ├── test_connectors/
│   │   │   └── test_workers/
│   │   ├── integration/               # Integration tests (API endpoints)
│   │   │   ├── __init__.py
│   │   │   ├── test_query_flow.py
│   │   │   ├── test_ingest_flow.py
│   │   │   ├── test_rbac_filtering.py
│   │   │   └── test_health_checks.py
│   │   └── evaluation/                # Golden Question Test Suite
│   │       ├── __init__.py
│   │       ├── test_golden_questions.py
│   │       ├── test_threshold_tuning.py
│   │       └── datasets/
│   │           └── golden_questions_v1.json
│   │
│   ├── scripts/                       # Utility Scripts
│   │   ├── seed_db.py                 # Database seeding (dev/test data)
│   │   ├── evaluate_golden_questions.py  # Golden Question runner (calls domain/services/evaluation_service.py)
│   │   ├── tune_threshold.py          # Threshold optimization (F1 maximization)
│   │   ├── migrate_index.py           # Blue-green reindex orchestration
│   │   ├── backup_db.sh               # Manual database backup
│   │   ├── restore_db.sh              # Database restore from backup
│   │   └── health_check.sh            # Health endpoint validation
│   │
│   ├── pyproject.toml                 # Poetry dependencies + project metadata
│   ├── poetry.lock                    # Locked dependency versions
│   ├── requirements.txt               # Pip fallback (generated from poetry)
│   ├── .env.example                   # Environment variables template
│   ├── pytest.ini                     # Pytest configuration
│   ├── mypy.ini                       # Type checking configuration
│   └── .flake8                        # Linting rules
│
├── frontend/                          # Next.js Frontend
│   ├── app/
│   │   ├── layout.tsx                 # Root layout with providers
│   │   ├── page.tsx                   # Landing page
│   │   ├── globals.css                # Global styles + Tailwind imports
│   │   │
│   │   ├── (query)/                   # Query Page Group
│   │   │   ├── layout.tsx             # Query-specific layout
│   │   │   ├── page.tsx               # Main query interface with SSE streaming
│   │   │   └── loading.tsx            # Loading state
│   │   │
│   │   ├── (admin)/                   # Admin Page Group (RBAC protected)
│   │   │   ├── layout.tsx             # Admin layout with nav
│   │   │   ├── page.tsx               # Admin dashboard
│   │   │   ├── sources/
│   │   │   │   └── page.tsx           # Source management page
│   │   │   ├── ingestion/
│   │   │   │   └── page.tsx           # Ingestion control page
│   │   │   ├── thresholds/
│   │   │   │   └── page.tsx           # Threshold tuning page
│   │   │   └── analytics/
│   │   │       └── page.tsx           # Query analytics dashboard
│   │   │
│   │   └── api/                       # API Routes (SSE proxy, auth)
│   │       ├── query/
│   │       │   └── route.ts           # SSE streaming proxy to backend
│   │       └── auth/
│   │           └── [...nextauth]/
│   │               └── route.ts       # NextAuth.js handlers
│   │
│   ├── components/                    # React Components
│   │   ├── query/
│   │   │   ├── QueryInput.tsx         # User input form with validation
│   │   │   ├── StreamingAnswer.tsx    # SSE token-by-token display
│   │   │   ├── CitationPanel.tsx      # Source citations with line links
│   │   │   ├── ConfidenceBadge.tsx    # High/Medium/Low indicator
│   │   │   └── ThumbsFeedback.tsx     # Thumbs up/down widget
│   │   ├── admin/
│   │   │   ├── IngestForm.tsx         # Repository URL input + validation
│   │   │   ├── SourceList.tsx         # Active sources + sync status table
│   │   │   ├── ThresholdTuner.tsx     # Runtime threshold adjustment slider
│   │   │   ├── AnalyticsDashboard.tsx # Query metrics visualization
│   │   │   └── IngestRunMonitor.tsx   # Real-time ingestion progress
│   │   ├── ui/                        # shadcn/ui Components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ... (other shadcn components)
│   │   └── layout/
│   │       ├── Header.tsx             # Global header with auth
│   │       ├── Footer.tsx             # Footer with links
│   │       ├── Sidebar.tsx            # Admin sidebar navigation
│   │       └── LoadingSpinner.tsx     # Loading indicator
│   │
│   ├── lib/                           # Utility Libraries
│   │   ├── api-client.ts              # Backend API wrapper with auth
│   │   ├── sse-handler.ts             # SSE connection manager
│   │   ├── auth.ts                    # NextAuth.js configuration
│   │   ├── utils.ts                   # Helper functions (cn, etc.)
│   │   └── constants.ts               # Frontend constants
│   │
│   ├── hooks/                         # Custom React Hooks
│   │   ├── useQuery.ts                # Query execution hook
│   │   ├── useSSEStream.ts            # SSE streaming hook
│   │   ├── useAuth.ts                 # Authentication hook
│   │   └── useDebounce.ts             # Debouncing utility hook
│   │
│   ├── types/                         # TypeScript Type Definitions
│   │   ├── api.ts                     # API request/response types
│   │   ├── query.ts                   # Query-related types
│   │   ├── source.ts                  # Source-related types
│   │   └── user.ts                    # User and auth types
│   │
│   ├── public/                        # Static Assets
│   │   ├── favicon.ico
│   │   ├── logo.svg
│   │   └── images/
│   │
│   ├── next.config.js                 # Next.js configuration
│   ├── tailwind.config.ts             # Tailwind CSS configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── package.json                   # NPM dependencies
│   ├── package-lock.json              # Locked NPM versions
│   ├── .eslintrc.json                 # ESLint rules
│   ├── .prettierrc                    # Prettier formatting
│   └── .env.local.example             # Frontend environment template
│
├── infra/                             # Infrastructure & Deployment
│   ├── docker/
│   │   ├── docker-compose.yml         # Production stack (Lightsail)
│   │   ├── docker-compose.dev.yml     # Development stack (local)
│   │   ├── docker-compose.test.yml    # Test environment stack
│   │   ├── Dockerfile.api             # FastAPI API container
│   │   ├── Dockerfile.worker          # Celery worker container
│   │   ├── Dockerfile.frontend        # Next.js frontend container
│   │   └── .dockerignore
│   │
│   ├── caddy/                         # Reverse Proxy & TLS
│   │   ├── Caddyfile                  # Caddy configuration (Let's Encrypt)
│   │   └── certs/                     # TLS certificates (gitignored)
│   │
│   ├── prometheus/                    # Monitoring Configuration
│   │   ├── prometheus.yml             # Prometheus scrape config
│   │   ├── alerts.yml                 # Alerting rules (SLO violations, resource exhaustion)
│   │   └── recording_rules.yml        # Pre-aggregated metrics
│   │
│   ├── grafana/                       # Dashboards & Visualization
│   │   ├── dashboards/
│   │   │   ├── user_experience.json   # Query latency, error rates, feedback
│   │   │   ├── system_health.json     # CPU, memory, disk, service availability
│   │   │   ├── rag_performance.json   # Retrieval metrics, similarity scores
│   │   │   └── cost_monitoring.json   # Token usage, spend tracking
│   │   ├── provisioning/
│   │   │   ├── datasources.yml        # Prometheus datasource config
│   │   │   └── dashboards.yml         # Dashboard auto-provisioning
│   │   └── grafana.ini                # Grafana configuration
│   │
│   ├── scripts/                       # Operational Scripts
│   │   ├── deploy.sh                  # SSH deployment to Lightsail
│   │   ├── rollback.sh                # Rollback to previous version
│   │   ├── backup.sh                  # PostgreSQL backup to S3 (daily cron)
│   │   ├── restore.sh                 # Restore from S3 backup
│   │   ├── logs.sh                    # Tail logs from all services
│   │   ├── restart_services.sh        # Safe service restart (worker-then-api)
│   │   ├── scale_workers.sh           # Scale Celery workers
│   │   ├── db_migrate.sh              # Run Alembic migrations on prod
│   │   └── health_check.sh            # Validate deployment health
│   │
│   └── terraform/                     # Infrastructure as Code (optional)
│       ├── main.tf                    # Lightsail VPS provisioning
│       ├── variables.tf               # Terraform variables
│       ├── outputs.tf                 # Output values (IP, DNS)
│       └── terraform.tfvars.example   # Variable values template
│
├── .github/                           # GitHub Actions CI/CD
│   └── workflows/
│       ├── ci.yml                     # Tests + linting + type checking
│       ├── deploy.yml                 # SSH deployment to Lightsail
│       ├── backup.yml                 # Scheduled backups (daily)
│       └── security_scan.yml          # Dependency vulnerability scanning
│
├── docs/                              # Documentation Root
│   ├── Backbond/                      # Core Architectural Documents (Canonical)
│   │   ├── PROJECT_OVERVIEW.md        # Executive summary, problem statement
│   │   ├── REQUIREMENTS.md            # Functional and non-functional requirements
│   │   ├── ARCHITECTURE.md            # System architecture (this file)
│   │   ├── DECISIONS.md               # Canonical engineering decisions
│   │   ├── TECH_STACK.md              # Technology choices, cost model
│   │   ├── OPERATIONS.md              # Operational procedures, emergency protocols
│   │   └── TESTING.md                 # Test strategy, Golden Questions framework
│   │
│   ├── 01_product/                    # Product Specifications
│   │   ├── PRODUCT_SPEC.md            # Detailed product requirements
│   │   ├── USER_STORIES.md            # User stories and acceptance criteria
│   │   └── MVP_SCOPE.md               # MVP feature scope and v2 roadmap
│   │
│   ├── 02_api/                        # API Documentation
│   │   ├── API.md                     # OpenAPI spec, endpoint documentation
│   │   ├── AUTHENTICATION.md          # JWT auth, token management
│   │   ├── RATE_LIMITING.md           # Rate limit policies and overrides
│   │   └── ERRORS.md                  # Error codes and handling
│   │
│   ├── 03_engineering/                # Engineering Guides
│   │   ├── BASELINES.md               # Performance baselines, Golden Questions (98/100)
│   │   ├── DEVELOPMENT_GUIDE.md       # Local setup, coding standards
│   │   ├── CONTRIBUTION_GUIDE.md      # How to contribute, PR process
│   │   └── TROUBLESHOOTING.md         # Common issues and solutions
│   │
│   ├── 04_security/                   # Security Documentation
│   │   ├── SECURITY_POLICY.md         # Security practices, vulnerability disclosure
│   │   ├── RBAC.md                    # Role-based access control details
│   │   ├── SECRETS_MANAGEMENT.md      # Encryption, key rotation
│   │   └── COMPLIANCE.md              # Compliance considerations (GDPR, SOC2)
│   │
│   ├── 05_operations/                 # Operations & Capacity
│   │   ├── CAPACITY.md                # Capacity planning, scaling triggers (96/100)
│   │   ├── DEPLOYMENT.md              # Deployment procedures, checklists
│   │   └── INCIDENT_RESPONSE.md       # Incident classification, escalation
│   │
│   ├── 06_observability/              # Monitoring & Observability
│   │   ├── OBSERVABILITY.md           # Metrics, logs, traces, alerting (98/100)
│   │   ├── DASHBOARDS.md              # Dashboard guide, key metrics
│   │   └── ALERTING.md                # Alert definitions, response procedures
│   │
│   ├── 07_runbooks/                   # Operational Runbooks
│   │   ├── HIGH_LATENCY.md            # Troubleshoot p95 latency spikes
│   │   ├── HIGH_ERROR_RATE.md         # Troubleshoot error rate increases
│   │   ├── DISK_FULL.md               # Disk space exhaustion recovery
│   │   ├── MEMORY_PRESSURE.md         # Memory exhaustion response
│   │   ├── CELERY_WORKER_DOWN.md      # Worker recovery procedures
│   │   ├── DB_CONNECTION_POOL.md      # PostgreSQL connection issues
│   │   └── INDEX_MISMATCH.md          # Embedding model/version mismatch recovery
│   │
│   ├── 08_governance/                 # Data Governance
│   │   ├── DATA_GOVERNANCE.md         # Data retention, privacy policies
│   │   ├── AUDIT_LOGGING.md           # Audit log requirements
│   │   └── DATA_LIFECYCLE.md          # Data ingestion, archival, deletion
│   │
│   └── 09_release/                    # Release Management
│       ├── CI_CD.md                   # CI/CD pipeline, deployment safety (92/100)
│       ├── VERSIONING.md              # Versioning strategy, changelog
│       └── ROLLBACK_PROCEDURES.md     # Rollback strategies and time targets
│
├── evaluation/                        # Golden Question Evaluation Framework (Single Canonical Location)
│   ├── datasets/
│   │   ├── golden_questions_v1.json   # 50-100 curated questions (BASELINES.md §1)
│   │   ├── pqs_v1.json                # Performance Query Set (200-500 queries, BASELINES.md §4.1)
│   │   └── load_profiles.json         # Load profile definitions (BASELINES.md §4.3)
│   ├── scripts/
│   │   ├── evaluate_golden_questions.py  # Full evaluation runner (calls backend evaluation_service)
│   │   ├── run_pqs.py                 # Performance query set execution
│   │   └── analyze_failures.py        # Failure taxonomy classification (8 categories)
│   └── results/
│       └── .gitkeep                   # Evaluation results (gitignored, stored in DB via evaluation_repo)
│
├── .gitignore                         # Git ignore patterns
├── .env.example                       # Root environment template
├── README.md                          # Project overview, getting started
├── LICENSE                            # MIT License
├── CHANGELOG.md                       # Version history and changes
└── CONTRIBUTING.md                    # Contribution guidelines

```

**Key Structure Principles:**

1. **Layered Architecture:** Clear separation between API, Domain, RAG Pipeline, and Infrastructure layers
2. **Repository Pattern:** Data access isolated in repositories, never imported directly into RAG pipeline
3. **Clean Dependencies:** Lower layers never import upper layers
4. **Type Safety:** `types/` directory provides cross-layer type contracts preventing circular imports; `rag/contracts/` ensures strongly typed pipeline I/O
5. **Evaluation Persistence:** `evaluation_result.py` domain model + `evaluation_repo.py` enables trend analysis and longitudinal Golden Question tracking
6. **Production-Ready:** Comprehensive testing, monitoring, operational runbooks, and deployment automation
7. **Documentation-First:** Every major component has corresponding documentation in `docs/`
8. **Single Source of Truth:** Root-level `evaluation/` directory is the canonical location (not duplicated in `backend/tests/`)
9. **Operational Excellence:** Scripts, runbooks, and monitoring for 24/7 production readiness

---

## Component Breakdown

### 0. Type System & Contracts (New in v1.6)

**Purpose:** Provide strongly typed, shared definitions preventing circular imports and contract drift.

#### 0.1 Cross-Layer Types (`app/types/`)

**app/types/ids.py**
```python
from typing import NewType

ChunkId = NewType('ChunkId', str)           # Pinecone vector ID
SourceDocId = NewType('SourceDocId', str)   # Canonical source document identifier
QueryId = NewType('QueryId', str)           # Unique query execution ID
RunId = NewType('RunId', str)               # Ingestion/evaluation run UUID
```

**app/types/retrieval.py**
- `RetrievalResult`: Wrapper for chunk + cosine_score + rerank_score
- `PreRerankSet`: Top-N results from vector search before reranking
- `PostRerankSet`: Top-K results after reranking + ordering

**app/types/generation.py**
- `Citation`: chunk_id, source_doc_id, url, text_snippet, start_line, end_line
- `ConfidenceLevel`: Enum(HIGH, MEDIUM, LOW) based on cosine similarity
- `GenerationResult`: answer_text, citations, confidence, tokens_used

**app/types/evaluation.py**
- `GoldenQuestion`: question_text, expected_sources, key_facts, should_refuse
- `FailureTaxonomy`: Enum of 8 categories (retrieval_miss, reranker_miss, chunking_miss, threshold_too_strict, citation_mismatch, ungrounded_claim, missing_key_facts, prompting_issue, operational_failure)
- `EvalRunResult`: run_id, timestamp, metrics (Hit Rate@K, Precision@K, etc.), per_question_results

**Usage Pattern:**
- **API Layer:** Imports from `app.types.*` for request/response schemas
- **Domain Layer:** Uses types for service method signatures
- **RAG Layer:** Never imports domain/db; uses only `app.types.*` for contract definitions

#### 0.2 RAG Pipeline Contracts (`app/rag/contracts/`)

**app/rag/contracts/retrieval_contracts.py**
```python
@dataclass
class PreRerankResults:
    query_embedding: List[float]
    top_n_chunks: List[RetrievalResult]  # from app.types.retrieval
    namespace: str
    retrieval_latency_ms: float

@dataclass
class PostRerankResults:
    top_k_chunks: List[RetrievalResult]
    primary_candidate: RetrievalResult
    primary_cosine_score: float
    primary_rerank_score: float
    rerank_latency_ms: float

@dataclass
class PromptContext:
    chunks: List[RetrievalResult]
    token_budget: int
    truncated: bool
```

**app/rag/contracts/generation_contracts.py**
```python
@dataclass
class AnswerDraft:
    text: str
    raw_citations: List[str]  # [Source 1], [Source 2], etc.
    llm_latency_ms: float
    tokens_used: int

@dataclass
class FinalAnswer:
    text: str
    citations: List[Citation]  # from app.types.generation
    confidence: ConfidenceLevel
    retrieval_only: bool  # True if LLM skipped due to budget
```

**Usage Pattern:**
- **RetrievalStage output:** Returns `PostRerankResults` (contract)
- **GenerationStage input:** Accepts `PostRerankResults`, returns `FinalAnswer`
- **Testing:** Mock contracts instead of entire stages for isolated unit tests

---

### 1. API Layer (FastAPI Controllers)

**Responsibility:** Thin controllers that validate input, call services, return responses.

#### 1.1 QueryController (query_routes.py)

**Endpoint:** `POST /api/v1/query`

**Flow:**
1. Validate input against QueryRequest schema
2. Inject current_user via auth dependency
3. Check rate limits via rate_limiter middleware
4. Call `QueryService.execute(request, current_user)`
5. Stream SSE tokens to client
6. Return refusal contract if threshold not met (HTTP 200 with sources)

**Compliance:**
- **FR-6.1:** SSE streaming
- **NFR-1.1:** Latency tracking via telemetry
- **DECISIONS 7.3:** Refusal contract (HTTP 200 + sources)

#### 1.2 IngestController (ingest_routes.py)

**Endpoint:** `POST /api/v1/ingest` (Admin only)

**Flow:**
1. Validate repo URL format
2. Check admin role via require_admin dependency
3. Call `IngestService.trigger_job(request)`
4. Return job_id / ingest_run_id for status polling

**Compliance:**
- **FR-1.2:** RBAC (admin only)
- **FR-2.1:** GitHub ingestion trigger

#### 1.3 AuthDependency (dependencies/auth.py)

**Purpose:** JWT validation + user claim injection.

**Process:**
1. Decode JWT token from Authorization header
2. Validate signature and expiration
3. Load user from UsersRepository
4. Return User object with claims (id, role, allowed_user_ids)

**Compliance:**
- **FR-1.1:** JWT authentication
- **NFR-4.2:** Least privilege (scoped tokens)

#### 1.4 MetricsController (metrics_routes.py)

**Endpoints:**
- `GET /metrics` (**canonical**)
- `GET /api/v1/metrics` (optional proxy route)

**Purpose:** Expose metrics for monitoring and autoscaling.

**Security:** No authentication required (internal metrics endpoint)

**Compliance:**
- **NFR-6.1:** Metrics tracking

#### 1.5 RateLimiterMiddleware (dependencies/rate_limit.py)

**Purpose:** Enforce query limits per user.

**Process:**
1. Build Redis key: `rate_limit:{current_user.id}`
2. Check current count in Redis
3. Compare against MAX_QUERY_RATE_PER_USER (50/hour)
4. Raise HTTP 429 if exceeded
5. Increment counter with TTL=1 hour

**Compliance:**
- **FR-5.1:** Rate limiting (50/hour per DECISIONS section 11)
- **NFR-7.1:** Cost control

---

### 2. Domain Layer (Business Logic)

**Responsibility:** Framework-agnostic business rules. Orchestrates RAG pipeline, ingestion, RBAC, safety, cost, and threshold access.

#### 2.1 QueryService (domain/services/query_service.py)

**Core Responsibility:** Orchestrate query execution from request to response.

**Process:**
1. Build RBAC filter via RBACService (**canonical visibility OR allowed_user_ids rule**)
2. **Pre-query index safety check via IndexSafetyService**
3. **Check budget via CostService** (if exceeded → retrieval-only mode)
4. Fetch threshold via **ThresholdService**
5. Call:
   - `RAGPipeline.run(query_text, rbac_filter, namespace, retrieval_only_mode, threshold)`
6. Apply refusal contract output rules (HTTP 200 + sources)
7. Log metrics to QueryLogsRepository (prompt_hash, latencies, scores, cost)
8. Return QueryResult (answer + sources + confidence + refusal_reason + cost_info)

**Compliance:**
- **FR-3.x:** RAG pipeline orchestration
- **FR-5.3:** Feedback loop logging
- **NFR-7.1:** Cost control integration
- **DECISIONS 7.1:** Pipeline stages
- **DECISIONS 9.2:** Retrieval-only mode enforcement

#### 2.2 IndexSafetyService (domain/services/index_safety_service.py) **[REQUIRED]**

**Purpose:** Validate index compatibility BEFORE retrieval.

**Process:**
1. Load Source index metadata from SourcesRepository:
   - `index_model_id`, `index_version`, `index_name` (if used), `namespace`
2. Compare against Settings:
   - `Settings.EMBEDDING_MODEL_ID`
   - `Settings.INDEX_VERSION`
3. If mismatch → raise HTTP 409 with ErrorCatalog:
   - EMBEDDING_MODEL_MISMATCH or INDEX_VERSION_MISMATCH
4. If match → allow QueryService to proceed to pipeline

**Compliance:**
- **DECISIONS 4.1:** HTTP 409 mismatch errors

#### 2.3 ThresholdService (domain/services/threshold_service.py) **[REQUIRED]**

**Purpose:** Domain-controlled access to retrieval thresholds (keeps DB out of RAG).

**Process:**
1. Query ThresholdsRepository by namespace and index_version
2. Return stored threshold or default 0.65
3. Provide update method used by EvaluationService/admin tooling

**Compliance:**
- **DECISIONS 7.2:** Runtime tuning without redeploy
- **Invariant B:** Threshold access stays in Domain

#### 2.4 IngestService (domain/services/ingest_service.py)

**Core Responsibility:** Trigger ingestion jobs and track ingestion runs.

**Process:**
1. Validate repo URL and namespace
2. Create `IngestRun` row (status=running) and obtain `ingest_run_id`
3. Queue IngestJobTask via Celery with `ingest_run_id`
4. Expose status polling via ingest_run_id
5. Source index metadata is finalized **ONLY by worker finalize step** after full success

**Compliance:**
- **Invariant A:** Source metadata updated only on success (atomic finalize)

#### 2.5 RBACService (domain/services/rbac_service.py)

**Core Responsibility:** Build permission filters for retrieval.

**Canonical Filter Construction:**
- `(visibility == "public") OR (allowed_user_ids $in [current_user.id])`

**Compliance:**
- **FR-1.3:** Permission-filtered retrieval
- **Invariant D:** Visibility + allowed_user_ids contract

#### 2.6 EvaluationService (domain/services/evaluation_service.py)

**Purpose:** Golden Question evaluation + F1-based threshold tuning + longitudinal tracking.

**Process:**
1. Load Golden Question set from `evaluation/datasets/golden_questions_v1.json`
2. Create `EvaluationRun` entity (run_id, timestamp, environment, config)
3. For each question:
   - Execute query via QueryService
   - Compare retrieved sources to expected sources
   - Classify failures using 8-category taxonomy (retrieval_miss, reranker_miss, etc.)
   - Record per-question result (hit, precision, recall, taxonomy)
4. Aggregate metrics: Hit Rate@K, Precision@K, Retrieval Recall, F1, Groundedness, Citation Accuracy, TNR, FRR
5. Suggest optimal threshold to maximize F1 (sweep 0.50-0.80 in 0.05 increments)
6. **Persist results via EvaluationRepository:**
   - Store EvaluationRun with aggregate metrics
   - Store per-question results with taxonomy classification
   - Enable trend analysis, regression detection, threshold tuning history
7. Update threshold via ThresholdService if tuning requested

**Compliance:**
- **DECISIONS 7.2:** Calibration rule (maximize F1)
- **BASELINES.md §1:** Golden Questions framework with 10 metrics + 8-category failure taxonomy
- **BASELINES.md §4.1:** PQS governance (distinct from Golden Questions)

**New in v1.6: Persistence Layer**
- Uses `evaluation_repo.py` to store run history in PostgreSQL
- Enables Grafana dashboards showing Golden Question metric trends over time
- Supports A/B testing of threshold changes with before/after comparison

#### 2.7 CostService (domain/services/cost_service.py) **[REQUIRED]**

**Purpose:** Track costs + enforce monthly spend caps.

**Process:**
1. Query current month spend from QueryLogsRepository
2. Sum token costs (embedding + LLM calls)
3. Compare to MONTHLY_SPEND_CAP_USD ($25)
4. Return BudgetStatus:
   - available | warning (>=80%) | exceeded
5. If exceeded → enforce retrieval-only mode (skip LLM generation)

**Compliance:**
- **NFR-7.1:** Monthly spend caps
- **DECISIONS 9.2:** Spend cap behavior

#### 2.8 HealthService (domain/services/health_service.py) **[REQUIRED]**

**Purpose:** Comprehensive dependency health checks for production monitoring.

**5 Concrete Checks (with timeouts):**
1. PostgreSQL: `SELECT 1` (2s)
2. Redis: `PING` (1s)
3. Pinecone: `describe_index_stats()` (3s)
4. OpenAI (optional): minimal embedding (5s) (does NOT fail overall health)
5. Celery: worker heartbeat freshness from Redis keys (Invariant F)

**Endpoints:**
- `GET /api/v1/health` (liveness: core dependencies)
- `GET /api/v1/ready` (readiness: all dependencies)

---

### 3. RAG Pipeline Layer (Retrieval + Generation)

**Responsibility:** Implement DECISIONS.md exactly. Pipeline is pure logic; DB access is handled in Domain and injected as inputs.

#### 3.1 RAGPipeline (rag/pipeline.py) **[THIN ORCHESTRATOR]**

**Inputs:** `query_text`, `rbac_filter`, `namespace`, `retrieval_only_mode`, `threshold`

**Process:**
1. Call `RetrievalStage.run(...)`
2. Call `RefusalStage.run(..., threshold=threshold)`
3. If refused → return refusal result
4. Else call `GenerationStage.run(...)`

---

#### 3.2 RetrievalStage (rag/stages/retrieval_stage.py)

**Stages:**

**Stage R1: Query Embedding**
- Check Redis cache for query embedding (TTL=24h)
- If cache miss, call OpenAI `text-embedding-3-small`
- Cache key: `sha256(query_text + model_id + index_version)`

**Stage R2: Vector Search**
- Query Pinecone with embedding (top_k=20)
- Apply namespace filter
- Apply RBAC metadata filter

**Stage R3: Reranking**
- Cross-encoder `ms-marco-MiniLM-L-6-v2`
- Batch size 20; reduce to 10 if CPU > 80%

**Stage R4: Ordering**
- Sort by rerank score descending
- For same-file chunks, preserve original line order

**Output (Required):**
- ordered candidates
- cosine scores + rerank scores for each candidate
- `primary_candidate` = candidate after ordering
- `primary_cosine_score` = cosine score of `primary_candidate`
- `primary_rerank_score` = rerank score of `primary_candidate`

---

#### 3.3 RefusalStage (rag/stages/refusal_stage.py)

**Stage F1: Threshold Refusal Check**
- Input threshold provided by Domain
- Compare `primary_cosine_score` against threshold (**cosine-only invariant**)
- If `primary_cosine_score < threshold` → refusal
- Refusal includes top 3 sources and reason="LOW_SIMILARITY"

**Output:** RefusalResult or Pass

---

#### 3.4 GenerationStage (rag/stages/generation_stage.py)

**Stage G1: Context Token Budgeting**
- Fit chunks within context_token_budget (1500)
- Preserve highest-scoring chunks first
- NO runtime deduplication (SimHash is ingestion-only)

**Stage G2: LLM Generation**
- If `retrieval_only_mode=True` → skip LLM, return sources-only response
- Else call `gpt-4o-mini` with SSE streaming
- Enforce response_token_budget (500)
- On LLM failure → fallback to retrieval-only response

**Stage G3: Citation Mapping**
- Parse [Source N] references in answer and map to chunk metadata

**Stage G4: Confidence Calculation**
- Confidence computed using `primary_cosine_score`:
  - HIGH >= 0.85
  - MEDIUM >= 0.70
  - LOW < 0.70

---

#### 3.5 Chunking Subsystem (rag/chunking/*)

**TokenChunker**
- 512 tokens, 50 overlap
- Enforce max_chunks_per_file (200)

**LineMapper**
- Tracks start_line/end_line per chunk

**Normalizer**
- Code-block aware normalization for hashing

**SimHashDedupe**
- 3-bit threshold
- Runs ONLY during ingestion

---

#### 3.6 Retrieval Subsystem (rag/retrieval/*)

**QueryEmbedder**
- Embedding model: `text-embedding-3-small`
- Cache key: `sha256(query_text + model_id + index_version)`
- TTL=24h

**VectorStoreClient**
- Pinecone query/upsert wrapper
- No post-retrieval safety checks (safety is pre-validated in Domain)

**CrossEncoderReranker**
- `ms-marco-MiniLM-L-6-v2` with CPU-based batch fallback

**RetrievalCacheKeyBuilder**
- Reserved for optional retrieval caching (see Caching Invariants)

---

#### 3.7 Generation Subsystem (rag/generation/*)

**PromptBuilder**
- Grounded prompt, strict refusal rules, citations using [Source N]

**AnswerGenerator**
- `gpt-4o-mini` with SSE streaming + fallback

**CitationMapper**
- [Source N] → file_path/source_url/start_line/end_line/snippet

**ConfidenceCalculator**
- Confidence from cosine similarity only (uses `primary_cosine_score`)

---

### 4. Connectors Layer (Data Sources)

**GitHubClient**
- Repo tree + file content retrieval using scoped token

**GitDiffScanner**
- added/modified/deleted/renamed detection
- rename mapping old_path → new_path

**IgnoreRules**
- .librarianignore + built-in blacklist

**FileSizeValidator**
- 1MB max file size enforcement

---

### 5. Workers Layer (Celery Background Jobs)

#### 5.1 IngestJobTask (Atomic Finalize Required)

1. Create or receive `ingest_run_id`
2. Fetch repo files
3. Apply IgnoreRules
4. Validate file sizes
5. Extract text (.md/.txt/.rst)
6. Chunk (TokenChunker + LineMapper)
7. Dedupe (SimHashDedupe ingestion-only)
8. Embed in batches (64)
9. Upsert to Pinecone with metadata contract (includes `ingest_run_id`)
10. Store chunk metadata in PostgreSQL (includes `ingest_run_id`)
11. Validate ingestion completeness (counts, invariants)
12. **Finalize (atomic):**
    - Update Source index metadata and `last_indexed_sha`
    - Mark IngestRun as finalized/succeeded
13. If any error occurs:
    - Mark IngestRun failed
    - Do NOT update Source metadata

#### 5.2 PurgeJobTask
- Delete vectors + metadata by file_path, namespace

#### 5.3 ReindexJobTask (Blue-Green)
- Free Tier: namespace switching (env_v1 → env_v2 → validate → swap in Postgres → delete old namespace)
- Paid Tier: dual-index swap using `index_name` with retention policy

#### 5.4 BackupJobTask
- Daily pg_dump → gzip → S3 upload → 7-day retention

#### 5.5 HeartbeatTask (Required)
- Every 30 seconds, each worker updates:
  - `celery_heartbeat:{worker_name}` in Redis with TTL=90 seconds

---

### 6. Persistence Layer (Repositories)

**UsersRepository**

**SourcesRepository**
- Stores: repo, namespace, last_indexed_sha, index_model_id, index_version, (optional) index_name
- Enforces atomic updates of index metadata after successful ingestion/reindex finalize

**ChunksRepository**
- Chunk CRUD + delete-by-file_path
- Stores `ingest_run_id` per chunk

**QueryLogsRepository**
- prompt_hash + redacted prompt + scores + feedback + latencies + costs

**ThresholdsRepository**
- get/update thresholds per namespace and index_version

**IngestRunsRepository**
- create/update ingest runs
- mark finalize/succeeded/failed

**EvaluationRepository (New in v1.6)**
- Stores Golden Question evaluation runs (EvaluationRun entity)
- Stores per-question results with 8-category failure taxonomy
- Enables longitudinal tracking: metric trends, regression detection, threshold tuning history
- Supports queries: get_recent_runs, get_trend(metric, days), compare_runs(run_id_a, run_id_b)

---

### 7. Cross-Cutting Concerns (Core Utilities)

**Settings (core/config.py)**
- Model IDs, INDEX_VERSION, budgets, threshold defaults, rate limits, ingestion limits

**AppLogger (core/logging.py)**
- Structured JSON logs + secret redaction

**ErrorCatalog (core/errors.py)**
- HTTP mappings and error codes:
  - EMBEDDING_MODEL_MISMATCH (409)
  - INDEX_VERSION_MISMATCH (409)
  - LOW_SIMILARITY (200 refusal contract)

**Telemetry (core/telemetry.py)**
- OTel spans for each stage + timing attributes

**Metrics Exporter (core/metrics.py)**
- Prometheus registry + `/metrics` endpoint implementation (canonical)

**No CostController in core.**
- Cost enforcement is Domain-only via CostService.

---
```
