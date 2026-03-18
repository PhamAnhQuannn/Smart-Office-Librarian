# MVP Scope

## Metadata
- Version: v1.0
- Status: Active MVP scope
- Last Updated: 2026-03-15

## In Scope (MVP)
- Authenticated query experience with SSE streaming.
- Citation-backed answers with confidence indicator.
- Admin-triggered ingestion pipeline for supported source types.
- Threshold-based refusal behavior and retrieval-only fallback modes.
- Operational baseline: CI/CD, backup/restore, deploy/rollback scripts.

## Out of Scope (Post-MVP)
- Multi-tenant isolation (`FR-7`).
- LLM judge fact-checking (`FR-3.7`).
- Advanced multi-region deployment.

## MVP Success Criteria
- Core query and ingest workflows are stable in production.
- Release and rollback paths are executable.
- Observability and security baselines are active.
- Documentation and runbooks match implemented behavior.

