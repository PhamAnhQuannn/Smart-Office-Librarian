# Versioning Policy

## Metadata
- Version: v1.0
- Status: Active
- Last Updated: 2026-03-15
- Owner: Engineering Team

## Scheme
Smart Office Librarian uses Semantic Versioning (`MAJOR.MINOR.PATCH`).

## Rules
- MAJOR: breaking API or contract changes.
- MINOR: backward-compatible features.
- PATCH: backward-compatible bug fixes and hardening.

## API Versioning
- Public API is namespaced by major version (`/api/v1/`).
- Breaking API changes require new namespace (`/api/v2/`).
- Existing major versions remain supported for a documented deprecation window.

## Release Tags
- Release tags follow `v<MAJOR>.<MINOR>.<PATCH>`.
- Example: `v1.6.0`.

## Build Metadata
Every release should capture:
- git commit SHA
- deployment environment
- release timestamp (UTC)
- index version and model ids when relevant to retrieval behavior

## Backward Compatibility Expectations
- PATCH and MINOR releases must preserve current API contracts.
- Database migrations must be backward-compatible for rolling deployment safety.
- Rollback path must remain valid for every production release.

## Deprecation Policy
- Deprecated API fields/endpoints are announced in release notes.
- Minimum deprecation window: one MINOR release cycle before removal.
- Removals occur only in MAJOR version upgrades.

