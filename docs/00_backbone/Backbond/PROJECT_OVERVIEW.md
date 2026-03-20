# 📚 Embedlyzer — Enterprise AI Knowledge Agent

## 📋 Executive Summary

**Embedlyzer** is a fully deployed, production-grade Retrieval-Augmented Generation (RAG) platform that unifies fragmented engineering knowledge into a single queryable interface. It enables developers to ask natural-language questions across GitHub repositories and receive AI-generated answers with direct citations to the original source files — including file path and line number.

- **Current Version:** v1.0 — live at `http://35.175.156.119`
- **Core Purpose:** Eliminate knowledge silos and accelerate developer onboarding across engineering teams.
- **Target Users:** Software Engineers, DevOps Engineers, and Technical Writers.
- **Key Value:** Semantic understanding of documentation with verifiable source attribution, a groundedness guardrail that refuses to hallucinate, and per-workspace usage quotas with a full observability stack.
- **Architecture:** Self-serve developer tool — every user owns their workspace. A 3-stage RAG pipeline (retrieval → refusal → generation) with vector search, reranking, and real-time SSE streaming. Two roles: regular users (full product) and platform admins (internal ops dashboard).

---

## 🎯 The Problem

In fast-growing engineering teams, knowledge becomes a critical bottleneck.

- **Fragmented Knowledge:** Information is split across GitHub repos, Confluence specs, and meeting notes — no single source of truth.
- **Keyword Failure:** Traditional search fails when users don't know the exact term. Semantic search finds answers even when vocabulary doesn't match.
- **Onboarding Friction:** New hires spend weeks locating tribal knowledge buried in outdated repositories, slowing down senior engineers with repetitive questions.

---

## 🏗️ System Architecture & Flow

The system follows a modular, multi-tenant architecture designed for reliability, verifiable retrieval, and safe generation.

**High-Level Flow:**
1. **Ingestion:** GitHub connector fetches Markdown, text, and code files → SimHash deduplication filters unchanged content → Text is split into overlapping chunks with line-number mapping preserved.
2. **Embedding:** Chunks are encoded into dense vectors using `text-embedding-3-small` via the OpenAI API. Embeddings are Redis-cached to reduce latency and cost.
3. **Storage:** Vectors are stored in Pinecone (one namespace per workspace); chunk metadata (file path, repo, start/end line, SHA) is stored in PostgreSQL.
4. **Retrieval:** User query is embedded → Pinecone top-k similarity search → cross-encoder reranker re-scores results for precision → primary cosine score is checked against a configurable threshold.
5. **Refusal:** If the primary score is below threshold, the pipeline refuses to generate and returns the top sources only — preventing hallucinated answers.
6. **Generation:** `gpt-4o-mini` synthesizes a cited answer using only the retrieved context. Responses stream token-by-token via Server-Sent Events (SSE).

### Core Components

| Component | Description |
|:---|:---|
| **GitHub Connector** | Fetches files via GitHub API with diff scanning (only re-ingests changed SHAs), `.gitignore`-aware filtering, and per-connector validation |
| **Chunker** | Semantic + token-based splitting, line-number mapping, SimHash duplicate detection, and text normalization |
| **Embedder** | OpenAI `text-embedding-3-small` with Redis embedding cache (configurable TTL) |
| **Vector Store** | Pinecone serverless — one namespace per workspace for strict data isolation |
| **Reranker** | Cross-encoder model re-scores top-k candidates before the refusal threshold check |
| **RAG Pipeline** | 3-stage orchestrator: retrieval → refusal → generation with retrieval-only budget mode |
| **Generation Stage** | Streaming `gpt-4o-mini` completions with citation-enforcing system prompt |
| **Celery Workers** | Background tasks for ingestion, re-indexing, vector purge, database backup, and worker heartbeat |
| **Quota Enforcement** | Per-workspace monthly query cap tracked atomically in Redis |
| **Threshold Tuner** | Admin UI + API to set per-namespace similarity thresholds; persisted in PostgreSQL |
| **Audit Logger** | Structured event log for all admin and ingestion actions |
| **Prometheus Metrics** | In-memory registry exposing latency histograms, query counts, refusal counts, TTFT, and active SSE streams |

---

## 🛠️ Tech Stack

| Layer | Technology | Notes |
|:---|:---|:---|
| **Backend** | FastAPI (Python 3.12) | Async, typed, OpenAPI auto-docs |
| **Task Queue** | Celery + Redis | Ingestion, reindex, purge, backup, heartbeat tasks |
| **Vector DB** | Pinecone (serverless) | Per-workspace namespaces for data isolation |
| **LLM** | OpenAI `gpt-4o-mini` | Budget-optimized; strong citation accuracy |
| **Embeddings** | OpenAI `text-embedding-3-small` | Redis-cached to minimize API calls |
| **Relational DB** | PostgreSQL 16 | Users, workspaces, sources, chunks, query logs, feedback, thresholds |
| **Cache / Broker** | Redis | Embedding cache, Celery broker, quota counters |
| **Frontend** | Next.js 14, Tailwind CSS, shadcn/ui | App Router, SSE streaming, server components |
| **Auth** | JWT (bcrypt) + Google OAuth 2.0 | Passwords nullable for OAuth-only accounts; `provider` claim in JWT |
| **Reverse Proxy** | Caddy 2 | Auto HTTPS via Let's Encrypt when a domain is set |
| **Observability** | Prometheus + Grafana | Pre-configured dashboards, `/metrics` endpoint |
| **Infra** | Docker Compose, AWS Lightsail | 8-container stack, 1-command deploy |

---

## ✅ What's Built & Deployed (v0.9.1)

### Backend API
- `POST /api/v1/auth/login` — JWT authentication
- `POST /api/v1/auth/register` — self-registration (toggled by `REGISTRATION_ENABLED`)
- `GET /api/v1/auth/google` + `GET /api/v1/auth/google/callback` — Google OAuth 2.0
- `POST /api/v1/auth/logout` — stateless session invalidation (204)
- `POST /api/v1/query` — SSE-streaming RAG query with refusal guardrail
- `GET /api/v1/history` / `DELETE /api/v1/history/{id}` / `DELETE /api/v1/history` — query history
- `POST /api/v1/workspace/ingest` — background GitHub ingestion (workspace-scoped, user-facing)
- `GET /api/v1/workspace/ingest-runs` — recent sync runs for the authenticated user's workspace
- `GET /api/v1/workspace/me` — workspace info + live usage stats (queries this month from Redis, chunks from DB, sources count)
- `GET /api/v1/workspace/sources` / `DELETE /api/v1/workspace/sources/{id}` — source management
- `POST /api/v1/feedback` — thumbs up/down on query results
- `GET /api/v1/admin/audit-logs` — structured audit log viewer (admin only)
- `GET /api/v1/admin/ingest-runs` — ingestion run list across all workspaces (admin only)
- `GET /api/v1/admin/evaluation/summary` — analytics (admin only)
- `GET /api/v1/admin/budget` + `PUT /api/v1/admin/budget/{id}` — workspace quota management (admin only)
- `GET /metrics` — Prometheus-format metrics
- `GET /health` + `GET /ready` — health and readiness probes

### Data Model
- **Users** — email/password or Google OAuth, role (`admin` / `user`), active flag
- **Workspaces** — one per user, Pinecone namespace = workspace slug, configurable quotas (`max_chunks`, `max_sources`, `monthly_query_cap`)
- **Sources** — GitHub repo + file metadata, last-indexed SHA for diff-based re-ingestion
- **Chunks** — text fragments with vector ID, SimHash, start/end line, namespace
- **QueryLogs** — full observability record per query (latency, TTFT, tokens, score, sources)
- **Feedbacks** — vote (`up` / `down`) + optional comment linked to query log
- **ThresholdConfigs** — per-namespace similarity threshold, persisted and versioned

### Frontend UI

**Main app (all users) — sidebar: Ask / Sources / Sync / History / Usage / Settings**
- **Ask (`/`)** — streaming answer with `[Source N]` citations, confidence badge, citation panel with file + line, thumbs feedback; guest mode supported (queries run, results not saved)
- **Sources (`/sources`)** — repositories grouped by repo (not file-per-row): repo card shows file count, "Added [date]", "Indexed" status chip, expandable file list, repo-level delete
- **Sync (`/sync`)** — connect a GitHub repo, choose "Fast sync" (incremental) or "Full refresh" strategy, monitor recent sync runs with Retry button on failed runs
- **History (`/history`)** — paginated query history; guest state shows sign-in prompt; per-item delete and clear-all
- **Usage (`/usage`)** — queries used this month + remaining, sources count, chunks stored vs limits (all live data from backend)
- **Settings (`/settings`)** — account info, sign-in method (Google OAuth / Email & password), Sign out button, answer quality explanation, danger zone
- **Login / Signup** — email/password + "Sign in with Google" button

**Platform admin dashboard (`/admin/*`) — hidden from regular users, hard role-check**
- **Ingestion** — trigger ingestion on any workspace (platform operator only)
- **Sources** — view and delete sources across all workspaces
- **Workspaces** — workspace quota management
- **Thresholds** — per-namespace similarity threshold tuning
- **Analytics** — query volume, refusal rate, feedback trends
- **Audit Logs** — structured admin event log
- **Budget** — token usage and cost tracking

### Infrastructure (8-container Docker Compose stack)
| Container | Role |
|:---|:---|
| `api` | FastAPI app (health-checked) |
| `worker` | Celery worker |
| `frontend` | Next.js app (health-checked) |
| `postgres` | PostgreSQL 16 (health-checked) |
| `redis` | Redis 7 (health-checked) |
| `caddy` | Reverse proxy (HTTP now; auto-HTTPS when domain set) |
| `prometheus` | Metrics scraping |
| `grafana` | Dashboards |

---

## 🔒 Security

- JWT tokens signed with a configurable secret; passwords hashed with bcrypt
- Google OAuth uses CSRF state cookie to prevent open-redirect attacks
- **2-role model**: every user is the full owner of their own workspace; platform admin (`/admin`) is for internal ops only
- RBAC enforced at every admin endpoint — role checked server-side, never client-side
- Admin UI hard-blocks non-admins client-side too (`role !== "admin"` → redirect to `/`)
- `hashed_password` is nullable — Google-only accounts cannot authenticate via password endpoint
- Pinecone namespace isolation ensures each workspace's vectors are logically separated
- Caddy serves `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` headers
- `REGISTRATION_ENABLED` flag allows admin-invite-only mode
- All admin and ingestion events are written to a structured audit log

---

## 🧪 Success Criteria

| Metric | Target | Status |
|:---|:---|:---|
| Retrieval Precision (Top-5) | > 80% | Measured via golden questions dataset |
| Query Latency (p95) | < 2 s | Tracked via `librarian_stage_latency_ms` histogram |
| Groundedness | 100% | Refusal guardrail refuses sub-threshold answers |
| User Satisfaction | > 4.0 / 5.0 | Thumbs feedback collected per query |

---

## 📂 Repository Structure

```
backend/          FastAPI app, Celery workers, RAG pipeline, connectors
  app/
    api/          REST routes (auth, query, ingest, workspace, admin, feedback)
    connectors/   GitHub connector (client, diff scanner, extractor, ignore rules)
    rag/          Pipeline orchestrator, retrieval, chunking, generation, refusal
    workers/      Celery tasks (ingest, reindex, purge, backup, heartbeat)
    db/           SQLAlchemy models, Alembic migrations, repositories
    core/         JWT security, metrics registry, audit logger
frontend/         Next.js 14 app
  app/(query)/    Main product UI (Ask, Sources, Sync, History, Usage, Settings)
  app/(auth)/     Login, Signup, Google callback
  app/admin/      Platform admin dashboard (Analytics, Thresholds, Budget, Audit)
  app/api/        Next.js route handlers (SSE proxy, auth proxy)
infra/
  docker/         Docker Compose (8-service production stack)
  caddy/          Reverse proxy config (auto-TLS ready)
  prometheus/     Scrape config
  grafana/        Dashboard provisioning
docs/             Architecture, API reference, runbooks, security policy
evaluation/       Golden questions dataset, PQS evaluation scripts
```

---

## ⚡ Quick Start (Local Dev)

```bash
# 1. Clone and configure
cp backend/.env.example backend/.env
# Fill in OPENAI_API_KEY, PINECONE_API_KEY, JWT_SECRET

# 2. Start all services
docker compose -f infra/docker/docker-compose.yml up --build

# 3. Run migrations and seed admin
docker compose -f infra/docker/docker-compose.yml exec api \
  sh -c "PYTHONPATH=/app alembic -c /app/alembic.ini upgrade head"
docker compose -f infra/docker/docker-compose.yml exec api \
  sh -c "PYTHONPATH=/app python3.12 /app/scripts/seed_db.py --admin-email admin@example.com --admin-password YourPassword123"

# 4. Open http://localhost
```

---

## 🔥 Resume Positioning

> "Designed and deployed a production multi-tenant RAG platform with GitHub ingestion, vector similarity search with cross-encoder reranking, a groundedness refusal guardrail, real-time SSE streaming, Google OAuth, per-workspace isolation, and a full observability stack (Prometheus + Grafana) — all containerised and live on AWS."