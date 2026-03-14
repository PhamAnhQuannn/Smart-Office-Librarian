# Audit Logging Foundation

## Scope

This document defines the Step 74 audit logging foundation for admin source and threshold changes.

## Event Coverage

- `audit.source.updated`
- `audit.source.deleted`
- `audit.threshold.updated`

## Required Fields

Each audit event must include these fields:

- `actor_id`
- `actor_role`
- `resource_type`
- `action`
- `resource_id`
- `changes`
- `retention_days`

## Retention Policy

- Minimum retention for operational audit logs: `14` days
- Step 74 records this as `retention_days=14` on emitted admin audit events
- Broader storage, purge, and compliance enforcement remain follow-up work under later NFR-4 slices

## Current Step Boundary

- In scope: admin source changes and threshold changes
- Out of scope: role-change audit coverage, full persistence layer, retention purge jobs, and TRACEABILITY promotion to complete
