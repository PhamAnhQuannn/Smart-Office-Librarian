# Security Policy

## Metadata
- Version: v1.0
- Status: Active
- Last Updated: 2026-03-15
- Owner: Security Team

## Policy Statement
Smart Office Librarian follows defense-in-depth with mandatory authentication, authorization, encryption, audit logging, and incident response controls.

## Mandatory Controls
- JWT authentication with server-side validation.
- Role-based authorization and admin gating for mutating endpoints.
- TLS for traffic in transit.
- Log redaction for credentials and sensitive fields.
- Audit logging for security-sensitive admin actions.
- Regular dependency vulnerability scans.

## Vulnerability Reporting
- Report security issues privately to the project security contact.
- Do not disclose exploitable details publicly before remediation.
- Include reproduction details, impact, and affected version where possible.

## Response Targets
- Critical vulnerabilities: triage within 24 hours.
- High vulnerabilities: triage within 72 hours.
- Medium/low vulnerabilities: triage within 7 days.

## Disclosure Process
1. Validate and reproduce.
2. Assign severity and owner.
3. Patch and test.
4. Deploy with rollback readiness.
5. Publish advisory and version impact summary.

