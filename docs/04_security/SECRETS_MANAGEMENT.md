# Secrets Management

## Metadata
- Version: v1.0
- Status: Active baseline
- Last Updated: 2026-03-15
- Owner: Security/Engineering

## Secret Types
- Database credentials
- Redis credentials
- JWT signing secrets/keys
- OpenAI/Pinecone API keys
- Backup/deployment secrets

## Storage Rules
- Local development: `.env` files excluded from source control.
- CI/CD: GitHub Actions encrypted secrets.
- Production: host-level secret store or environment variables injected at runtime.

## Handling Rules
- Never commit plaintext secrets.
- Never print secrets to logs, errors, or metrics.
- Redact sensitive values in structured logs.
- Principle of least privilege for all tokens and credentials.

## Rotation Policy
- Routine rotation: every 90 days for long-lived credentials.
- Emergency rotation: immediate on suspected leak.
- Rotation events must be auditable and linked to incident/change records.

## Validation Checklist
- Secrets present before deployment preflight.
- Missing secret detection fails fast in workflows/scripts.
- Post-rotation validation includes health and readiness checks.

