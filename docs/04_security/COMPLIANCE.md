# Compliance Baseline

## Metadata
- Version: v1.0
- Status: Active baseline
- Last Updated: 2026-03-15
- Owner: Security/Engineering

## Scope
This document defines the minimum compliance controls for MVP operations.

## Control Families
- Access Control: JWT auth, role-based authorization, admin-only mutation routes.
- Data Protection: TLS in transit, secret handling policy, log redaction.
- Auditability: structured audit events for admin source and threshold changes.
- Retention: operational logs and data retention windows documented and enforced.
- Recovery: daily backups and restore drills documented.

## Current Evidence
- TLS/edge routing baseline: `infra/caddy/Caddyfile` and related tests.
- Admin audit coverage: `docs/08_governance/AUDIT_LOGGING.md`.
- Retention controls: `backend/tests/integration/test_data_retention.py`.
- Backup/restore procedures: `infra/scripts/backup.sh`, `infra/scripts/restore.sh`.

## Compliance Check Cadence
- Weekly: dependency and vulnerability scan review.
- Monthly: access review for admin roles and deployment credentials.
- Quarterly: recovery drill and incident/postmortem process validation.

## Exceptions
- Any control exceptions require written approval and expiry date.
- Exceptions must include risk owner and remediation plan.

