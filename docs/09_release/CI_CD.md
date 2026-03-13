# CI/CD Pipeline Documentation  
**Project:** Smart Office Librarian  
**Version:** v1.3  
**Status:** Production CI/CD Procedures  
**Last Updated:** 2026-03-11  
**Compliance:** TECH_STACK.md v1.2, OPERATIONS.md v1.3, ARCHITECTURE.md v1.6, DECISIONS.md v1.5  

---

# 1. Overview

This document defines the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the Smart Office Librarian Retrieval-Augmented Generation (RAG) system.

The pipeline is designed for:

- Budget-optimized single-host production (Amazon Lightsail VPS)
- Production-grade reliability and rollback safety
- Strict quality enforcement
- Clear environment isolation
- Reversible deployments

---

## 1.1 Pipeline Philosophy

- **Automated Quality Gates** — No manual testing required for standard releases.
- **Fail Fast** — Linting, typing, testing, and build validation must pass before deployment.
- **Near-Zero Downtime (MVP)** — Health-checked restarts on a single host (brief restart blip possible).
- **Rollback-Ready** — Every deployment must be reversible within minutes.
- **Cost-Aware** — Uses GitHub Actions free tier and server-side Docker builds.

---

## 1.2 Infrastructure Model

| Component | Platform |
|-----------|----------|
| CI/CD Platform | GitHub Actions |
| Deployment Target | Amazon Lightsail (2GB VPS) |
| Container Runtime | Docker + Docker Compose (v2 plugin: `docker compose`) |
| Deployment Method | SSH-based remote execution |
| Environment Approval | GitHub Environments (required reviewers for production) |

---

# 2. Environments

The system maintains three strictly isolated environments.

| Environment | Purpose | Infrastructure | Pinecone Namespace | Deployment Trigger |
|------------|---------|---------------|-------------------|-------------------|
| **dev** | Local development | Developer machine | `dev` | Manual |
| **staging** | Pre-production validation | Lightsail 1GB VPS or isolated instance | `staging` | Push to `staging` branch |
| **prod** | Live production traffic | Lightsail 2GB VPS | `prod` | Push to `main` + manual approval |

---

## 2.1 Production Approval Mechanism

Production deployment requires:

- GitHub Environment protection rules
- Required reviewer approval
- CI checks passing (required status checks)
- No force pushes allowed

The deployment job cannot execute until GitHub Environment approval is granted.

---

## 2.2 Environment Configuration Hierarchy

Configuration sources (highest priority first):

1. Environment Variables (`.env`)
2. Docker Compose overrides
3. Application defaults (code-level configuration)

Environment variables are **never overwritten by deployments**.

---

## 2.3 Isolation Guarantees

### Database Isolation
- Separate database per environment (`librarian_dev`, `librarian_staging`, `librarian_prod`)
- Production database backed up daily

### Vector Database Isolation
- Pinecone namespace separation: `dev`, `staging`, `prod`
- No cross-environment retrieval possible

### Redis Isolation
- Separate Redis DB index per environment (0/1/2)
- Required key prefix per environment (`prod:`, `staging:`, `dev:`)

### Secret Isolation
- Unique secrets per environment
- Production secrets never used in staging or dev

---

# 3. Source Control & Branching Strategy

## 3.1 Branch Model

Primary branches:

- `main` — Production-ready, always deployable
- `staging` — Pre-production validation
- `develop` — Optional integration branch

Supporting branches:

- `feature/*`
- `bugfix/*`
- `hotfix/*`

---

## 3.2 Branch Protection Rules

### Main Branch
- Requires pull request
- Requires at least one approval
- Requires required status checks to pass (all required CI checks)
- Disallows force push
- Enforces up-to-date branches before merge

### Staging Branch
- Requires required status checks to pass
- Allows controlled merges from feature branches

---

## 3.3 Commit Conventions

Conventional Commits format required:

- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `test:`
- `chore:`
- `perf:`
- `ci:`

---

# 4. Continuous Integration (CI)

The CI pipeline runs automatically on:

- Push to `main`
- Push to `staging`
- Feature branches
- Pull requests targeting `main` or `staging`
- Nightly scheduled audit

---

## 4.1 CI Stages

1. Code checkout
2. Backend linting
3. Backend static typing
4. Backend unit tests (≥ 80% coverage)
5. Frontend linting
6. Frontend unit tests (≥ 70% coverage)
7. Integration tests (for staging/main only)
8. Security audit gate (blocking policy below)
9. Docker build validation

---

## 4.2 Quality Gates

The following conditions must pass:

- Zero linting violations
- Strict typing enforcement
- Minimum backend coverage: 80%
- Minimum frontend coverage: 70%
- Integration tests must pass (when applicable)
- No critical security vulnerabilities

High severity vulnerabilities block only if:

- Runtime dependency (not dev-only), AND
- Fix/patch exists, AND
- Vulnerability is reachable in typical production execution paths

Medium/Low: logged and tracked; do not block merges.

---

## 4.3 Required Status Checks Policy (Enforcement)

Branch protection must enforce **required status checks** for `main` and `staging`.

- All required CI jobs must pass before merge.
- If an “aggregate CI success” check is used, it must depend on all CI jobs and be marked required.
- Deployments must not be used as a substitute for CI gating.

---

## 4.4 CI Performance Target

- Target execution time: < 8 minutes (p95)
- Concurrency control prevents duplicate parallel runs on same branch

---

# 5. Continuous Deployment (CD)

Deployment occurs only after:

- CI passes (required status checks)
- Security gate passes
- Manual approval (production)
- Required environment variables validated

---

## 5.1 Deployment Safety Principles

- Deployment scripts execute remotely via SSH.
- Remote execution must use protected quoting to avoid local variable expansion.
- All critical steps must fail-fast (`set -euo pipefail`).
- Preflight checks validate Docker availability and environment configuration prior to migrations.
- Deployments do not overwrite `.env` or secrets.

---

## 5.2 Deployment Process (High-Level)

1. Validate environment readiness (preflight)
2. Pull latest code on server
3. Rotate database backups (retain last 7)
4. Create pre-migration database backup
5. Generate migration preview
6. Apply safe migrations
7. Tag current images for rollback
8. Build updated images on server
9. Restart worker
10. Restart API
11. Validate health endpoint
12. Validate readiness endpoint
13. Record release metadata
14. Monitor for regression

---

## 5.3 Near-Zero Downtime Clarification

Because production runs on a **single VPS instance**, restarts are health-checked but may cause a brief restart blip.

This is acceptable under MVP constraints.

True zero-downtime (multi-instance rolling) requires horizontal scaling and load balancing, planned for future scale phases.

---

# 6. Health & Readiness Contract

## 6.1 Health Endpoint

Checks:
- PostgreSQL connectivity
- Redis connectivity

Returns:
- HTTP 200 if healthy

---

## 6.2 Readiness Endpoint

Checks:
- PostgreSQL connectivity
- Redis connectivity
- Pinecone availability
- Worker heartbeat freshness

Returns:
- HTTP 200 only if system is ready to serve traffic

---

## 6.3 Worker Heartbeat Requirement

Celery worker must:

- Write heartbeat key to Redis
- Update every 15 seconds
- TTL set to 60 seconds

If heartbeat key expires, readiness endpoint must fail.

---

# 7. Rollback Strategy

Rollback must be possible within minutes.

---

## 7.1 Rollback Triggers

Automatic rollback conditions:

- Error rate > 20% sustained
- Latency p95 > 5s sustained
- Dependency failure
- Data integrity issues

Manual rollback conditions:

- Silent logic errors
- Performance regression
- Security issue discovered post-deploy

---

## 7.2 Rollback Methods

1. Git commit rollback
2. Docker image rollback (using locally tagged images)
3. Database restore from pre-migration backup
4. Full system restore (last stable commit + DB restore)

---

## 7.3 Rollback Time Targets (Operational Expectations)

Best-effort rollback targets (vary by DB size and VPS performance):

- **Code rollback:** ≤ 5 minutes
- **Image rollback:** ≤ 3 minutes
- **DB restore rollback:** ≤ 15 minutes
- **Full system rollback:** ≤ 30 minutes

---

## 7.4 Post-Rollback Requirements

Within 24 hours:

- Root cause analysis
- Postmortem documentation
- Regression test added
- Deployment checklist updated

---

# 8. Release Metadata Requirements

Each deployment must record:

- Commit SHA
- Deployment timestamp (UTC)
- Deployed by (GitHub actor)
- Environment
- Migration preview stored under release directory

The API must expose a build information endpoint that returns, at minimum:

- commit SHA
- deployed_at (UTC)
- environment

---

# 9. Secrets Management

Production secrets:

- Stored in `.env` on server
- File permission restricted
- Optional encrypted backup in secure vault

CI/CD secrets:

- Stored in GitHub Actions secrets
- Never committed to repository

---

# 10. Backup & Retention

- Database backup created before every migration
- Retain last 7 backups
- Older backups rotated
- Backup restore procedure tested quarterly

---

# 11. Monitoring & Deployment Observability

Post-deployment monitoring window: 15 minutes minimum.

Track:

- Error rate
- Query latency p95
- Dependency availability
- Worker heartbeat freshness
- CPU/memory usage

Alert if:

- Error rate > 10% sustained
- Latency > 3s sustained
- Health check failures detected

---

# 12. Cost Controls

- CI usage remains within GitHub free tier
- Docker images built on server (no registry cost)
- Security scans optimized to reduce runtime minutes
- Budget caps enforced via environment configuration

---

# 13. Compliance Alignment

This CI/CD pipeline enforces:

- Environment isolation (OPERATIONS.md)
- Safe migration invariants (ARCHITECTURE.md)
- Cost controls (DECISIONS.md)
- Observability standards (OBSERVABILITY.md)
- Capacity triggers (CAPACITY.md)

---

# Version History

| Version | Date | Changes |
|----------|------|---------|
| v1.0 | 2026-03-11 | Initial CI/CD documentation |
| v1.1 | 2026-03-11 | Added rollback tagging, worker heartbeat, near-zero downtime clarification |
| v1.2 | 2026-03-11 | Hardened deploy invariants: SSH quoting requirement, preflight env validation, backup rotation policy, improved rollback guarantees, clarified production approval enforcement |
| v1.3 | 2026-03-11 | Clarified required status checks enforcement; clarified security gate enforcement policy; added rollback time targets; made build-info expectations explicit |

---

**Document Status:** Approved for Implementation  
**Next Review:** June 10, 2026  