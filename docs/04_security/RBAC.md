# RBAC Policy

## Metadata
- Version: v1.0
- Status: Active
- Last Updated: 2026-03-15
- Owner: Security/Engineering

## Roles
- `user`: query + feedback access.
- `admin`: user permissions plus ingestion and administrative operations.

## Permission Matrix
| Capability | user | admin |
|---|---|---|
| Query (`POST /api/v1/query`) | allow | allow |
| Feedback (`POST /api/v1/feedback`) | allow | allow |
| Ingest (`POST /api/v1/ingest`) | deny | allow |
| Threshold/source admin operations | deny | allow |

## Enforcement Rules
- Role is derived from server-validated JWT claim.
- Unauthorized requests return `401`.
- Authenticated but disallowed requests return `403`.
- Role checks run before mutation logic.

## Retrieval Access Filter
Canonical retrieval filter:
- `(visibility == "public") OR (allowed_user_ids contains user.id)`

## Audit Requirements
- Admin actions must emit structured audit events.
- Audit records include actor identity, role, action, resource id, and bounded changes payload.

