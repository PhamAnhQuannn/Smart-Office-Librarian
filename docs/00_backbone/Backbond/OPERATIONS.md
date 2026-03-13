# 🚀 OPERATIONS — Smart Office Librarian

**Version:** v1.3
**Status:** Operational Procedures (Non-Executable)
**Last Updated:** 2026-03-11
**Architecture:** v1.5

> This document defines **operational procedures** for deploying, monitoring, and maintaining the Smart Office Librarian RAG system.
>
> **Non-Executable Policy:** This file contains **no command blocks, no scripts, and no code snippets**. It is purely descriptive. Any executable content belongs in separate runbooks or scripts (e.g., `infra/scripts/`, `RUNBOOKS/`).

---

## 0. Scope, Roles, Severity, and Operational Defaults

### 0.1 Operational Roles (Minimum Required)

* **Engineering (Owner)**
  Owns correctness of application behavior, Architecture invariants, release contents, and test/evaluation baselines.

* **Operator / SRE**
  Owns deployments, rollback execution, monitoring/alerting configuration, capacity management, and incident response coordination.

* **Security (or Security Delegate)**
  Owns secrets management policy, rotation, vulnerability management SLAs, and access audits.

### 0.2 Incident Severity Model

* **SEV-1 (Critical)**
  System unavailable or unsafe behavior (e.g., persistent 5xx surge, DB down, readiness failing across fleet, security breach). Immediate response required.

* **SEV-2 (High)**
  Major degradation (e.g., sustained p95 latency breach, ingestion failures blocking core workflows, budget exceeded unexpectedly with high impact).

* **SEV-3 (Medium/Low)**
  Minor degradation or localized issues (single source ingestion failing, small regression, non-critical alert noise).

Escalation and response expectations (paging, on-call schedule, handoffs) must be defined per organization.

### 0.3 Operational Defaults (Binding Decisions)

These defaults are the operational stance unless an ADR explicitly overrides them:

* **Redis degraded mode**

  * Embedding cache: **disabled automatically** when Redis is unavailable.
  * Rate limiting: **fail-open** (do not block requests if Redis-backed limiter is unavailable).
  * Operational guardrail: when fail-open is active, Operations must treat this as a **SEV-2 risk** and apply compensating controls (see Incident Response).

* **LLM provider outage stance (Production)**

  * The system **may continue in retrieval-only mode** when the LLM provider is unavailable.
  * Readiness policy for LLM: **LLM is optional for readiness** *only if* retrieval-only mode is functioning and the system is otherwise healthy.
  * This condition must still trigger **alerting** (performance/feature degradation), typically **SEV-2** if sustained.

* **Health vs readiness gating (Production)**

  * Health requires: **PostgreSQL + Redis reachable** (core runtime state and control-plane).
  * Readiness requires: **PostgreSQL + Redis + Pinecone reachable**, and **worker freshness healthy** if worker freshness is implemented as a readiness gate.
  * If worker freshness is not implemented, readiness must explicitly document the alternative gate (e.g., queue health).

* **Index swap rule**

  * Active index/namespace selection is controlled by **Source metadata in PostgreSQL**, not environment config edits.
  * Swaps occur only via **validated blue-green operations** with **atomic metadata updates**.

* **Threshold change control**

  * Threshold changes are treated as **production configuration changes** and must be reviewed, logged, and monitored after application.

---

## 1. Deployment

### 1.1 Required Infrastructure

The production system requires the following dependencies to be provisioned and reachable from the API and worker runtime:

* **PostgreSQL (15+)**
  Persistent storage for users, sources, chunk metadata, query logs, thresholds, and operational state.

* **Redis (7+)**
  Used for:

  * query embedding cache (if enabled)
  * rate limiting counters (if Redis-backed)
  * Celery broker and/or result backend (depending on implementation)
  * optional worker heartbeat store (if chosen as the heartbeat source)

* **Pinecone (Vector Store)**
  Used for vector retrieval and metadata-filtered search.

  * Free tier operational strategy: **namespace swap** (blue-green reindex via namespace change)
  * Paid tier operational strategy: **dual-index swap** (blue-green reindex via index name change)

* **Celery Workers**
  Used for ingestion, purge, reindex, and backup jobs.

* **LLM Provider (OpenAI or configured alternative)**
  Used for query embeddings and (when enabled) LLM generation.

---

### 1.2 Environments (Dev / Staging / Prod)

Operations MUST maintain clear separation across environments:

* **Development (dev)**
  Highest observability, lowest blast radius. Used for rapid iteration and debugging.

* **Staging (staging)**
  Production-like behavior and configuration. Used for validating migrations, release candidates, and operational changes.

* **Production (prod)**
  Highest reliability and security posture. Only controlled changes permitted.

Environment-specific policies MUST be defined and documented (at minimum):

* budget caps and cost guardrails
* tracing sampling rates
* evaluation acceptance criteria and baseline metrics
* log retention and access restrictions
* operational SLOs (latency, availability, refusal bands)

---

### 1.3 Configuration Management (Operational Rules)

This system follows Architecture v1.5 invariants. Operational configuration MUST respect:

#### A) Budget Cap Source of Truth

* The **monthly spend cap is controlled by runtime configuration** (environment config mapped into Settings) and enforced by `CostService`.
* Operations must ensure the configured cap matches the intended environment policy (dev/staging/prod).
* The cap must be monitored continuously and treated as a production guardrail.

#### B) Index Compatibility Source of Truth (DB > Env)

* **Source index metadata stored in PostgreSQL is the canonical selector** for retrieval compatibility and the active index/namespace:

  * `namespace` (active free-tier mechanism)
  * `index_name` (optional paid-tier mechanism)
  * `index_model_id`
  * `index_version`
  * `last_indexed_sha`
* Environment configuration provides defaults only for bootstrap/initial setup.
* After onboarding sources, runtime relies on Source metadata as the authoritative reference.

**Operational rule:** Do not change the active index/namespace by editing environment configuration. Swaps occur only through validated blue-green operations that update Source metadata atomically.

#### C) Index Metadata Atomicity

* Source metadata MUST be updated only after:

  * a full successful ingestion, or
  * a successful reindex validation.
* Failed or partial ingestion MUST NOT update:

  * `index_model_id`, `index_version`, `namespace`, `index_name`, `last_indexed_sha`.

#### D) Redis Degraded Mode Policy (Chosen Policy)

Redis outages must follow a single, consistent operational stance:

* Embedding cache becomes unavailable and performance may degrade.
* Rate limiting is **fail-open** when Redis-backed enforcement cannot be applied.
* Background jobs are impacted if Redis is the broker; ingestion/reindex/backups may stall.

This policy must be aligned with implementation and alerting, and compensating controls must be available for production safety.

---

### 1.4 Health vs Readiness Semantics

Operations MUST maintain consistent meanings:

* **Health (liveness)** indicates the service process is running and core control-plane dependencies are reachable.
  Health should remain stable under partial dependency failures where the system can degrade.

* **Readiness** indicates the service can safely serve end-user traffic at full fidelity (or approved degraded fidelity).

**Binding dependency requirements (prod defaults):**

* Health requires: **PostgreSQL + Redis reachable**
* Readiness requires: **PostgreSQL + Redis + Pinecone reachable**, plus:

  * worker freshness healthy if worker freshness is implemented, otherwise a defined equivalent gate must exist
* LLM provider:

  * if retrieval-only is accepted (default), LLM may be optional for readiness but must produce alerts when unavailable
  * if retrieval-only is not accepted in a specific environment, that environment must explicitly override readiness gating via ADR

---

### 1.5 Deployment Validation Checklist (Pre-Deployment)

Before deploying any change to production:

* Unit tests pass and coverage meets the target.
* Integration tests pass.
* Golden Question evaluation meets acceptance criteria for the target environment.
* Security scanning is clean (no critical issues).
* Database migrations validated on staging.
* Configuration changes reviewed and recorded in DECISIONS/ADRs if they alter runtime behavior.
* Operational dashboards/alerts updated if new metrics or behavior changes were introduced.

---

### 1.6 Deployment Procedure (Zero-Downtime Behavior)

Operationally, deployments must preserve availability:

* **API Layer:** rolling replacement so existing connections remain stable.
* **Workers:** graceful shutdown so running jobs either complete or are safely re-queued.
* **Frontend:** deployed in a way that preserves SSE behavior (no buffering, no premature termination).

Post-deployment validation must confirm:

* health is healthy
* readiness is healthy (per environment gates)
* metrics are available
* authentication works (JWT validation)
* rate limiting behaves as expected (including degraded-mode stance)
* SSE query streaming remains correct end-to-end

---

### 1.7 SSE Operational Requirements (Proxy / Load Balancer)

To preserve streaming correctness, edge infrastructure MUST support:

* long-lived HTTP connections without response buffering
* timeouts that exceed expected stream duration under peak load
* concurrency consistent with expected simultaneous streams
* no transformations that break event framing or incremental delivery

SSE behavior MUST be monitored via synthetic checks that validate end-to-end streaming behavior and completion.

---

### 1.8 Rollback Policy

Rollback MUST be treated as first-class:

* Roll back application deployments to the last known-good version.
* Roll back migrations only if the migration is explicitly reversible and reversal risk is acceptable.
* After rollback, validate:

  * health/readiness
  * SSE query streaming
  * ingestion safety invariants (atomic metadata)
  * operational metrics stability (latency/refusal/cost)

---

### 1.9 Blue-Green Reindex Operations (Index Lifecycle)

A reindex is required when:

* embedding model changes, OR
* index schema changes (`INDEX_VERSION` change), OR
* corruption/major ingestion failures require rebuilding.

#### Reindex Validation Standard (Operational Gate)

A blue-green swap MUST be gated on a defined validation standard:

* **Validation set:** representative smoke queries plus (recommended) a subset of Golden Questions.
* **Pass criteria (minimum):**

  * high success rate (no systemic failures)
  * **zero** embedding/index mismatch errors (HTTP 409 class must not appear)
  * refusal rate remains within the accepted band for the environment (see SLOs)
  * latency sanity check does not regress beyond defined thresholds
* **Abort criteria:**

  * any mismatch storm behavior
  * systematic query failures
  * validation results outside refusal/latency bounds
* **Post-swap monitoring window:** must be defined (commonly measured in hours) and used to decide whether to keep or revert.

#### Free Tier Strategy: Namespace Swap

* New namespace is built and validated.
* Queries continue using the current namespace during the build.
* Only after validation succeeds is the active namespace swapped atomically (via Source metadata update).

#### Paid Tier Strategy: Dual-Index Swap

* New index is built and validated.
* Queries continue using the current index during the build.
* Only after validation succeeds is the active index swapped atomically (via Source metadata update).

**Operational invariant:** queries must never observe a partially built index/namespace as active.

---

## 2. Monitoring & Observability

### 2.1 Metrics (Prometheus)

The system exposes a Prometheus-compatible metrics endpoint.

Operational focus areas:

* query throughput and latency (p50/p95/p99)
* refusal rate (threshold correctness)
* retrieval-only rate (budget enforcement and LLM outage impact)
* ingestion job success/failure rates
* cost and budget utilization
* dependency health gauges
* worker freshness (heartbeat age) if implemented

### 2.2 Alerting (Alertmanager)

Alerts should be configured for:

#### Critical Dependency Failures

* PostgreSQL down
* Redis down
* Pinecone down
* workers stale / missing heartbeat beyond the acceptable window (if heartbeat is used)

#### Feature Degradation (Approved Degraded Modes)

* LLM unavailable while retrieval-only is serving (alert as degradation)
* Redis rate limiter unavailable with fail-open active (alert as cost/abuse risk)

#### Performance Degradation

* sustained p95 latency above SLO
* sustained rise in refusal rate beyond operational threshold
* sustained upstream failures (LLM provider, Pinecone)

#### Cost Guardrail Breaches

* budget warning (≥80%)
* budget exceeded (≥100%), confirming retrieval-only mode activation and elevated monitoring

#### Ingestion Failures

* failure rate above threshold over sustained period
* repeated failures for the same connector/source class

### 2.3 Logging (Structured + Redacted)

Logging must be:

* structured (JSON recommended)
* consistent across API and workers
* safe by default (strict redaction)

Must never log:

* raw authorization headers
* full API keys
* PII in prompts
* raw file contents

Should log:

* prompt hashes
* stage latency breakdowns
* refusal reasons
* error codes and sanitized error context
* job IDs and source identifiers
* administrative changes (threshold updates, swaps) with audit context (who/when/what scope)

### 2.4 Distributed Tracing (OpenTelemetry)

Tracing must enable root-cause analysis across:

* Query path: API → Retrieval → Refusal → Generation
* Ingestion path: API → Worker pipeline steps → DB updates

Operational requirements:

* environment-based sampling (higher in dev, lower in prod)
* always sample errors
* propagate request IDs across services and workers

---

## 3. Maintenance

### 3.1 Routine Operational Tasks

#### Daily

* Validate readiness for core dependencies.
* Monitor worker freshness (if implemented) within target.
* Monitor budget utilization and retrieval-only rate.
* Monitor refusal rate and query latency against SLO.
* Review mismatch errors (HTTP 409 class) for early index drift.

#### Weekly

* Review error patterns and recurring incident themes.
* Check database size growth and index health.
* Verify backup restoration in a non-prod environment.
* Run Golden Question evaluation and compare to baseline.
* Tune thresholds if refusal rate drifts outside target.

#### Monthly

* Apply dependency updates (security-first).
* Review cost breakdown and reduce token usage if needed.
* Reassess rate limits and cost guardrails.
* Perform PostgreSQL maintenance strategy (vacuum/analyze as defined).
* Verify monthly budget reset behavior at month boundary.
* Review access audits and vulnerability posture.

### 3.2 Threshold Tuning Operations

Threshold tuning is required when:

* refusal rate is too high (coverage suffering), OR
* refusal rate is too low (hallucination risk increases), OR
* corpus changes meaningfully (new repos, large diffs).

Operational procedure:

* run evaluation suite against Golden Questions
* select threshold maximizing F1 (per Architecture/Decisions)
* update threshold **scoped by namespace and index_version**
* monitor refusal rate and evaluation metrics after change
* revert if metrics degrade

**Change control requirement:** threshold changes must be auditable (actor, scope, before/after) and monitored post-change.

### 3.3 Database Maintenance Operations

Operational requirements (binding defaults unless overridden by ADR):

* backups are automated on a defined schedule
* backups have a defined retention window
* restore tests are performed routinely
* table growth is monitored (query logs and chunk metadata)

**Default policy (recommended baseline):**

* Backup frequency: **daily**
* Backup retention: **7 days**
* Restore test cadence: **weekly** (non-prod)
* QueryLogs retention: **1 year active**, then archive to an approved cold storage location per compliance needs

#### Data Retention (Must Be Enforced)

Retention policies MUST be defined and enforced for:

* QueryLogs retention duration and archival strategy
* backup retention window
* deletion and archival audit requirements
* reversibility expectations for archival procedures

### 3.4 Worker Operations

Operational expectations:

* ability to scale workers horizontally under load
* safe shutdown and restart semantics
* retry policy observability (retries visible in logs/metrics)
* quarantine strategy for poison jobs (jobs that repeatedly fail)

Heartbeat:

* heartbeat source must be explicitly defined (Redis key vs DB table).
* readiness logic must match the selected heartbeat store and age thresholds.

---

## 4. Incident Response

### 4.1 Query Latency Spike

Primary diagnostics:

* Pinecone latency and error rate
* upstream LLM latency and error rate (if generation enabled)
* DB connection pool saturation
* Redis health and cache hit ratio
* worker CPU load and reranker fallback behavior

Primary mitigations:

* temporarily increase capacity (API/workers)
* reduce reranker workload (if supported operationally)
* temporarily enforce retrieval-only mode (if needed and allowed)
* degrade gracefully when Redis cache is unavailable

### 4.2 Index Mismatch Storm (HTTP 409)

Symptom:

* surge in HTTP 409 errors for embedding model mismatch or index version mismatch.

Root cause class:

* runtime Settings no longer match Source index metadata, OR
* reindex required but not completed, OR
* incorrect swap/metadata update occurred.

Operational mitigation:

* confirm active Source metadata values (namespace/index_name, model_id, index_version)
* confirm runtime Settings values
* perform validated blue-green reindex and swap only after validation passes
* never force swap to unvalidated index/namespace

### 4.3 High Refusal Rate

Diagnostics:

* ingestion freshness and recent ingestion failures
* threshold drift or accidental admin change
* wrong namespace/index active
* query distribution shifted outside corpus

Mitigations:

* confirm correct active index metadata
* run evaluation and retune threshold
* reindex if ingestion quality is suspect

### 4.4 Ingestion Failures

Common causes:

* connector rate limiting
* file limit violations
* upstream embedding failures
* vector store outages
* DB write failures

Operational invariant:

* ingestion failure must not alter Source index metadata (atomicity).

### 4.5 Budget Exceeded

Expected behavior:

* system enforces retrieval-only mode automatically (approved degraded mode).
* users receive sources without LLM-generated answers.

Operational response:

* confirm budget metrics and retrieval-only rate
* review cost drivers (embedding vs generation)
* reduce token usage where possible
* adjust budget only via controlled change management

### 4.6 Redis Rate Limiter Unavailable (Fail-Open Active)

Risk:

* abuse/cost spike risk while rate limiting is not enforced.

Operational response expectations (non-executable):

* treat sustained fail-open as a SEV-2 operational risk
* increase monitoring sensitivity for request volume and spend
* apply compensating controls available at the edge (proxy/WAF/admission control), per organization policy
* restore Redis-backed enforcement as the priority remediation

---

## 5. Production Readiness Checklist

### 5.1 Infrastructure

* PostgreSQL durability and HA posture defined
* Redis durability posture defined (persistence strategy)
* Pinecone capacity and tier aligned to workload
* worker scaling plan validated
* proxy/load balancer supports SSE reliably (no buffering)
* CDN strategy defined for frontend assets

### 5.2 Security

* secrets managed outside plaintext configuration (secrets manager)
* key rotation schedule enforced
* TLS everywhere
* hardened CORS and security headers
* vulnerability scanning and patch SLAs enforced

### 5.3 Monitoring

* metrics scraped and dashboards built
* alerts tested via drills
* tracing configured and validated end-to-end
* centralized log aggregation configured

### 5.4 Data Quality

* Golden Question set prepared and maintained
* evaluation thresholds tuned per environment
* ingestion verified on representative repos
* RBAC visibility behavior validated (public/private/shared)

### 5.5 Documentation

* Architecture / Testing / Operations reviewed and consistent
* ADRs updated for operationally significant changes
* runbooks exist for key failure modes and recovery steps (separate executable artifacts)

---

## 6. Disaster Recovery

### 6.1 Complete Database Loss

Recovery must include:

* restore from latest backup
* verify schema and row-level integrity
* validate query and ingestion paths after restore

RTO/RPO targets must be explicitly defined and periodically tested.

### 6.2 Vector Index Corruption

Recovery must include:

* build new index/namespace from source
* validate with representative queries
* swap atomically only after validation succeeds

### 6.3 Total System Failure

Recovery order:

* persistent storage (PostgreSQL)
* application runtime (API)
* worker runtime (Celery)
* vector access (Pinecone)
* caches (Redis)
* frontend availability

---

## 7. Capacity Planning

Capacity planning must be based on:

* query volume and concurrency
* ingestion throughput
* vector store constraints
* DB growth rates (query logs, chunk metadata)
* cost constraints (token usage)
* SSE connection concurrency limits at the edge

Scaling triggers should be explicitly defined for:

* DB pool saturation
* Redis memory pressure
* Pinecone latency/rate limit pressure
* worker queue backlog
* SSE concurrency saturation

Numeric sizing estimates should live in environment-specific capacity artifacts (e.g., `CAPACITY.md`) and be reviewed regularly.

---

## 8. Security Operations

### 8.1 Secrets Rotation

A rotation cadence must exist for:

* JWT secrets
* DB credentials
* Redis credentials (if used)
* Pinecone API keys
* LLM provider keys
* connector tokens (e.g., GitHub)

Rotation must be:

* logged
* validated with health/readiness checks
* performed with safe deployment semantics
* followed by revocation of old secrets after a defined grace window

### 8.2 Access Control Audits

Periodic audits must review:

* admin access list
* credential usage patterns
* RBAC visibility changes (audit trail)
* suspicious access patterns in logs

### 8.3 Vulnerability Management

Operational SLAs should define:

* patch time targets by severity
* staging validation requirements
* rollback readiness requirements

---

## 9. Change Management

### 9.1 Configuration Changes

Process:

* document decision (ADR)
* test in staging
* deploy in a controlled window
* monitor for regression
* capture lessons learned

### 9.2 Dependency Updates

Process:

* assess changelog and breaking changes
* run full test suite
* deploy via rolling update
* monitor for regressions

---

## 10. Post-Mortems

All significant incidents must produce a post-mortem including:

* timeline
* root cause
* resolution
* action items with owners
* preventive improvements
* documentation updates

---

**Document Owner:** Engineering Team
**Last Updated:** March 11, 2026 (v1.3)
