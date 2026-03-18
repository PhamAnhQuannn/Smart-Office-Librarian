# Changelog

All notable changes to Embedlyzer are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Domain model dataclasses for all persisted entities (`User`, `Source`, `Chunk`, `ThresholdConfig`, `QueryLog`, `Feedback`, `IngestRun`, `EvaluationResult`, `BudgetStatus`).
- Application type aliases and enumerations (`UserId`, `SourceId`, `ConfidenceLevel`, `GenerationMode`, `RefusalReason`, `Page[T]`, `RetrievalHit`, `RetrievalResult`).
- Pydantic v2 API schemas for all v1 endpoints (`auth`, `query`, `ingest`, `feedback`, `source`, `common`).
- Integration tests for health check endpoints (13 tests) and RBAC filtering (14 tests).
- Frontend admin pages: ingestion, sources, thresholds, analytics.
- Frontend BFF routes: `/api/query` (SSE proxy) and `/api/auth/[...nextauth]` (login/logout).
- `useDebounce` React hook.
- Abstract `BaseConnector` with `ConnectorFile`, `ConnectorError`, `ConnectorNotFoundError`.
- `scripts/seed_db.py` — development database seeder.
- `scripts/migrate_index.py` — Pinecone index migration utility.
- Full documentation: API auth, errors, rate limiting; development guide; contribution guide; troubleshooting; alerting; dashboards; 7 operational runbooks; data lifecycle policy.
- Root `.env.example` with all required environment variables.

---

## [1.0.10] — 2026-03-11

### Added
- Production-ready API contract (`docs/02_api/API.md` v1.0.10).
- RBAC namespace filtering applied at vector-search time.
- Confidence bands: HIGH / MEDIUM / LOW based on cosine score.
- Grounded-response / refusal contract (never returns hallucinated answers).
- Rate limiting: 50 requests/hour rolling window per user (FR-5.1).
- Concurrency limit: 5 active SSE streams per user.
- Budget / degraded mode: token budget tracking with auto-refusal when exhausted.
- Blue-green reindex guarantees via `index_version` column.
- Atomic ingestion with duplicate-detection via simhash.

### Changed
- Threshold default raised to 0.75.
- Chunk size fixed at 512 tokens with 50-token overlap.

---

## [1.0.0] — 2025-12-01

### Added
- Initial release of Embedlyzer RAG service.
- FastAPI backend with PostgreSQL + Pinecone.
- Next.js 14 frontend with admin and query interfaces.
- GitHub connector for automated code ingestion.
- JWT authentication with role-based access control.
- Celery worker for async ingestion.
- Prometheus metrics and Grafana dashboards.
- Docker Compose full-stack deployment.
