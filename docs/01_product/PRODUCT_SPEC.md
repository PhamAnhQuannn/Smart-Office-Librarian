# Product Specification

## Product
Smart Office Librarian (Embedlyzer)

## Problem Statement
Teams need a reliable way to answer operational and engineering questions from internal knowledge sources without hallucination-prone freeform responses.

## Target Users
- Engineers and operators who query documentation and runbooks.
- Administrators who manage source ingestion and relevance controls.

## Core Features
- Authenticated query endpoint with streaming output.
- Source citation panel with file and line-level evidence.
- Confidence signaling from retrieval similarity.
- Refusal behavior when context confidence is insufficient.
- Admin ingestion controls and feedback capture loop.

## Functional Contracts
- Query endpoint: `POST /api/v1/query` (SSE on success).
- Ingest endpoint: `POST /api/v1/ingest` (admin only).
- Feedback endpoint: `POST /api/v1/feedback`.
- Health/readiness: `/health`, `/ready`.
- Metrics endpoint: `/metrics`.

## Non-Functional Targets
- Query latency p95 <= 2.0 seconds under MVP load envelope.
- Availability target 99.9% monthly for API layer.
- Security controls for auth, RBAC, logging hygiene, and retention.

## Release Readiness Requirements
- CI and deployment preflight gates pass.
- Infrastructure manifests and operations scripts are executable.
- Recovery procedures and runbooks are documented.

