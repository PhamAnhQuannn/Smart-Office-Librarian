# Rollback Procedures

## Metadata
- Version: v1.0
- Status: Active
- Last Updated: 2026-03-15
- Owner: Engineering Team

## Purpose
This document defines the operational rollback path for Smart Office Librarian releases.

## Rollback Triggers
- Health or readiness checks fail after deploy.
- Error-rate spike persists beyond SLO threshold.
- Critical regression in query, ingest, auth, or metrics endpoints.
- Security issue requiring immediate revert.

## Preconditions
- Release metadata exists under `infra/releases/`.
- Deployment history file exists: `infra/releases/deploy_history.log`.
- Operator has Docker and compose access on target host.
- Environment secrets remain intact and are not modified by rollback.

## Standard Rollback Command
```bash
infra/scripts/rollback.sh --environment prod
```

## Explicit Release Rollback Command
```bash
infra/scripts/rollback.sh --environment prod --target-release <release-id>
```

## Rollback Flow
1. Identify target release from `infra/releases/deploy_history.log`.
2. Confirm release metadata file exists: `infra/releases/<release-id>.env`.
3. Execute rollback command.
4. Run post-rollback verification (`infra/scripts/health_check.sh`).
5. Confirm release state updated in `infra/releases/current_release_<env>.txt`.
6. Record incident and rollback evidence in operations ticket.

## Post-Rollback Verification
- API health endpoint returns 200.
- API readiness endpoint returns ready.
- Metrics endpoint is reachable.
- Frontend endpoint is reachable.
- Admin operations (`ingest`, threshold update, source update) are functional.

## Recovery Escalation
If rollback fails:
1. Freeze further deployments.
2. Restore database from last known-good backup if data integrity is impacted.
3. Open SEV incident and run incident response process.
4. Attach rollback logs and compose output to postmortem.

