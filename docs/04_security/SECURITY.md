# Security Documentation

**Version:** v1.0.4
**Status:** Production Security Requirements
**Last Updated:** 2026-03-11
**Compliance:** REQUIREMENTS.md v1.5 (FR-1.x, NFR-4.x), ARCHITECTURE.md v1.6, API.md v1.0.10

> This document defines the complete security model for the Smart Office Librarian RAG system, including authentication, authorization, encryption, data protection, operational security controls, input validation, and supply-chain safeguards.

---

## Overview

The Smart Office Librarian implements defense-in-depth security with multiple layers:

* **Authentication:** JWT bearer tokens with strict server-side validation
* **Authorization:** Role-Based Access Control (RBAC) with vector search-time filtering
* **Encryption:** TLS 1.3 in transit; encryption at rest for secrets + storage volumes/backups
* **Data Protection:** Snippet sanitization, PII redaction, logging hygiene
* **Operational Controls:** Rate limiting, audit logging, retention policies, incident response
* **Supply Chain Controls:** CI/CD hardening, dependency and artifact integrity
* **Input Validation:** Request size and content limits to prevent resource exhaustion

**Security Principles:**

* Fail-closed (deny by default)
* Server-authoritative (never trust client claims)
* Defense in depth (multiple security layers)
* Least privilege (minimal required permissions)
* Auditability (comprehensive logging of security events)

---

## 0. Environment Isolation & Trust Boundaries (Required)

### 0.1 Environment isolation (required)

Deployments MUST isolate `dev`, `staging`, and `prod` environments:

* Separate namespaces and configuration
* Separate credentials/keys per environment
* Separate data stores or strict schema separation per environment
* Never reuse production secrets in non-production environments
* JWT issuers/audiences MUST be environment-specific (see 1.1.4)

### 0.2 Service trust boundaries (required)

Services MUST follow least-privilege boundaries:

* **Query/API service** MUST NOT have access to connector credentials (cannot decrypt them).
* **Ingestion worker service** is the only component permitted to decrypt connector tokens for ingestion.
* DB roles MUST be separated (e.g., API read/write only for query logs; worker has ingestion write privileges).
* Secret material MUST never transit through logs or be returned by any API responses.

---

## 1. Authentication & Authorization

### 1.1 Primary Authentication (JWT)

**Mechanism:** JWT Bearer tokens (per REQUIREMENTS.md FR-1.1)

**Token Format:**

Header: `Authorization: Bearer <jwt_token>`

**Required Claims (server authoritative):**

* `sub` (string): Canonical user ID (used for RBAC filtering)
* `role` (string): User role (`admin` | `user`)
* `exp` (integer): Token expiration (Unix epoch seconds)

**Security Rules:**

1. Server MUST validate token signature, `sub`, and `exp` before granting access.
2. Authorization decisions MUST be based on server-side identity and policies.
3. Client-injected claims (e.g., `allowed_user_ids`) are non-authoritative hints ONLY.
4. Never use client-provided claims to grant access without server-side verification.

**Error Responses:**

* `401 Unauthorized`: Missing, invalid, or expired token
* `403 Forbidden`: Valid token but insufficient privileges for requested operation

#### 1.1.1 JWT signing algorithms (required)

* Allowed algorithms MUST be explicitly configured.
* Preferred: asymmetric signing (**RS256** or **ES256**) to separate sign/verify responsibilities.
* If using symmetric signing (**HS256**), the signing key MUST be high-entropy (256-bit minimum) and protected as a production secret.
* Algorithm confusion attacks MUST be prevented (do not accept `alg=none`; do not accept unexpected algorithms).

#### 1.1.2 Token lifetime & refresh

**Token Lifetime:**

* Recommended maximum: 1 hour for user tokens, 15 minutes for admin tokens.
* Implement token refresh mechanism for long-lived sessions.

#### 1.1.3 Revocation model (required)

Because JWTs are stateless, deployments MUST define a revocation strategy:

* **Default (recommended):** short TTL + refresh tokens; revoke by disabling refresh and waiting for TTL expiry.
* **Optional (stronger):** maintain a denylist keyed by `jti` (token id) in Redis or DB; reject tokens whose `jti` is revoked.
* Revoked tokens MUST NOT be accepted by any verification point.
* Revoked access MUST take effect deterministically (revoked tokens MUST fail validation via denylist, or via disabled refresh + TTL expiry).
* Revocation events MUST be auditable (who revoked, when, why).

**Revocation semantics (required clarity):**

* If a denylist (`jti`) is used, verification MUST consult the denylist and treat denied `jti` as invalid immediately. Denylist entries SHOULD be cached with a very short TTL and invalidated on update.
* If TTL-only revocation is used, deployments MUST ensure refresh tokens are immediately invalidated and TTLs are short enough for acceptable risk.
* Revocation testability: revocation operations MUST be observable and testable (revoked `jti` returns 401 at verification point).

#### 1.1.4 Issuer, audience, and time validation (required)

To prevent token reuse across environments/services, servers MUST validate:

* `iss` (issuer) against an allowlist for the current environment (`dev`/`staging`/`prod`)
* `aud` (audience) matches the intended API/service audience
* Optional but recommended: `nbf` (not-before) if present
* Clock skew allowance MUST be small and explicit (recommended: ≤ 60 seconds, configurable per deployment)

Tokens failing `iss`/`aud`/time checks MUST be rejected with `401 Unauthorized`.

#### 1.1.5 Key management, rotation, and `kid` (required)

Deployments MUST support key rotation without downtime:

* JWT header MUST include `kid` (key id) for all signed tokens.
* Verification MUST be performed using a server-managed key set keyed by `kid`.
* Key sets SHOULD be distributed via an internal JWKS-style mechanism (even if not public), or equivalent controlled key distribution.
* Rotation cadence:

  * Recommended routine rotation: **quarterly**
  * Emergency rotation: **within 24 hours** of confirmed compromise (or faster per operator policy)
* Grace period:

  * Old verification keys MUST be retained for at least the maximum token TTL + clock skew window to avoid breaking in-flight tokens.
* Key compromise or rotation events MUST be auditable.
* Key rotation or compromise events MUST trigger high-severity alerts and an emergency response playbook execution (see Section 10).

**Production key storage (required clarity):**

* Private signing keys for JWTs SHOULD be stored and used from a managed KMS or HSM (AWS KMS, Cloud KMS, HashiCorp Vault with HSM, or equivalent).
* Direct filesystem storage of unencrypted private keys is discouraged in enterprise deployments.
* Key usage and rotation operations MUST be auditable via the KMS/HSM audit trail where available.

#### 1.1.6 JWKS distribution & verification caching (required)

* Deployments MUST expose an internal JWKS-style endpoint or equivalent key distribution mechanism for services that verify JWTs.
* JWKS endpoints MUST be authenticated and access-controlled (internal network controls and/or mTLS).
* Verifiers MUST fetch the key set at startup and periodically refresh.

  * Recommended refresh behavior: fetch-on-start, then poll at a configurable interval (recommended: every 60 seconds), and refresh immediately on unknown `kid` or verification failures attributable to key changes.
  * Verifiers SHOULD cache verification keys for a short TTL (recommended: 5 minutes) to tolerate transient JWKS unavailability without accepting stale keys indefinitely.
* Verification SHOULD tolerate transient network failures via retry/backoff; rotation procedures MUST be compatible with verifier refresh behavior to avoid downtime.
* JWKS endpoints and verifier behavior MUST be documented in runbooks.

#### 1.1.7 Idempotency-Key (required for certain endpoints)

**Purpose:** Prevent replayed or retried requests from causing duplicate side effects or cost attacks.

**Requirements:**

* Support `Idempotency-Key` HTTP header on request paths that may cause billing/costly generation (e.g., POST query/generation endpoints).
* `Idempotency-Key` MUST be scoped per user (server must bind keys to `sub`) and must be unguessable (>=128 bits of entropy recommended).
* The system MUST persist the idempotency key (or a secure hash) and its response for a retention window of **24 hours** by default (configurable).
* Subsequent requests with the same user + `Idempotency-Key` MUST return the original response (or a clearly defined idempotent status) and MUST NOT cause duplicate generation or charging.
* Keys MUST be logged (hashed) and stored under access controls; raw idempotency keys MUST NOT appear in logs.
* If the stored response has expired, a new request with the same key is treated as a fresh request (server MAY return 409 Conflict or accept as new depending on implementation but MUST document behavior).
* Implement rate-limiting/validation to prevent abuse of idempotency storage (e.g., key flood attacks).

---

### 1.2 Stream Token Authentication (Browser SSE)

**Purpose:** Short-lived tokens for browser `EventSource` GET requests (per API.md)

**Mechanism:**

* Server emits `meta` SSE event containing `stream_token` after accepting POST `/api/v1/query`
* Browser uses token in GET `/api/v1/query/stream?query_id=<id>&token=<stream_token>`

**Security Requirements:**

1. **Cryptographic Signing:**

   * Stream tokens MUST be cryptographically signed (HMAC-SHA256 minimum) or use equivalent tamper-evident mechanism
   * Tokens MUST be unguessable (128+ bits of entropy)

2. **Scoping:**

   * Token MUST be bound to `(user_id, query_id, expiration)`
   * Token MUST NOT authorize access to any query other than the specified `query_id`
   * Token MUST NOT authorize access for any user other than the original requester

3. **Lifetime:**

   * Default TTL: 60 seconds (`STREAM_TOKEN_TTL`)
   * Tokens expire automatically after TTL
   * Expired tokens return `401 Unauthorized`

4. **Replay Policy:**

   * **Default (multi-use):** Token may be reused within TTL window (supports reconnects)
   * **Optional (single-use):** Token authorizes exactly one successful attachment; subsequent uses return `401`

5. **Leakage Prevention:**

   * Operators MUST NOT log query strings containing `token` parameter
   * Redact `token` at proxy/application logging layer
   * Set `Referrer-Policy: no-referrer` or `strict-origin` on streaming responses
   * Prevent navigation to third-party origins while tokenized URL is in browser history

**Cookie-Based Alternative (if implemented):**

* MUST implement CSRF protection (SameSite cookies + CSRF token or double-submit cookie)
* Document CSRF strategy in deployment guide
* Never rely on unauthenticated GET streams

---

## 2. Role-Based Access Control (RBAC)

### 2.1 Roles (per REQUIREMENTS.md FR-1.2)

**Two roles in MVP:**

1. **User:**

   * Query-only access
   * Can submit feedback
   * Rate limited to 50 queries/hour (REQUIREMENTS.md FR-5.1)
   * Subject to RBAC filtering (sees only permitted sources)

2. **Admin:**

   * All User privileges
   * Ingestion control (trigger/monitor ingestion jobs)
   * Source management (create/delete sources, modify visibility)
   * Threshold tuning (adjust refusal thresholds per namespace)
   * Access to admin endpoints (`/api/v1/admin/*`)
   * Query log access for troubleshooting (see Section 6 access controls)

**Role Enforcement:**

* Role derived from JWT `role` claim (server-validated)
* Admin-only endpoints return `403 Forbidden` for non-admin users
* Role checks occur before any business logic execution

---

### 2.2 Permission-Filtered Retrieval (Canonical)

**Enforcement Point:** Vector search metadata filter (per REQUIREMENTS.md FR-1.3, ARCHITECTURE.md Invariant D)

**Canonical RBAC Rule:**

A chunk is retrievable if:

* `visibility == "public"`, OR
* `allowed_user_ids` contains authenticated user's `sub` claim

**Visibility Semantics (MVP v1):**

1. **`public`:**

   * Visible to all authenticated users
   * `allowed_user_ids` MUST be empty array

2. **`private`:**

   * Visible only to users explicitly listed in `allowed_user_ids`
   * `allowed_user_ids` MUST be non-empty array of user IDs

**Future (v2): `shared` with group-based access:**

* `allowed_user_ids` may contain group identifiers (format: `group:<id>`)
* Server resolves group membership via identity service
* **Fail-closed behavior:** If identity service unavailable, treat group membership as empty (deny access)
* Group resolution failures do NOT crash queries; proceed with `public` and explicit user-id access only

**Critical Rules:**

1. **No post-retrieval filtering:** RBAC MUST be enforced in vector search metadata filter
2. **Prevent leakage:** All sources in responses (including refusal mode) MUST be RBAC-filtered
3. **No wildcards:** Never implement `allowed_user_ids=["*"]` patterns

**Admin bypass (diagnostic-only):** (required, narrow scope)

* Admin bypass for diagnostics MUST be explicit, auditable, and operator-controlled only. To be clear:

  * **Scope:** Admin bypass MAY be implemented **only** to override source *visibility* for diagnostic purposes (e.g., to inspect ingestion or indexing issues) — it MUST **NOT** bypass per-user RBAC when returning query results to arbitrary users.
  * **Controls:** Any use of admin bypass MUST:

    * Be requested with a justification string and the target `resource_id`/`source_id`;
    * Require an approver distinct from the requester (see break-glass controls in Section 6) for raw query text access or elevated bypass;
    * Be time-limited and scope-limited (e.g., 1-hour window, explicit resource identifiers);
    * Generate audit events recording who requested, who approved, the justification, time window, and data accessed.
  * **Prohibitions:** Admin bypass MUST NOT be used to return unfiltered, user-scoped query results to other users, nor to exfiltrate raw source content outside approved troubleshooting activities.
  * **Operator control:** Feature-flagged or operator-controlled bypass must be disabled in high-assurance deployments unless additional governance processes are in place.

**Cache Coherency:**

* Retrieval cache keys (if implemented) MUST include RBAC scope
* Never share cached results across users with different permissions (ARCHITECTURE.md Invariant C)

---

## 3. Data Encryption

### 3.1 Data in Transit (per REQUIREMENTS.md NFR-4.1)

**Protocol:** TLS 1.3 (minimum TLS 1.2)

**Requirements:**

* All client-server communication MUST use TLS
* Certificate validation MUST be enforced
* HTTP connections MUST redirect to HTTPS (except health checks on internal networks)
* Use strong cipher suites only (disable weak ciphers: RC4, 3DES, MD5-based)

**Certificate Management:**

* Use Let's Encrypt or enterprise CA
* Automate certificate renewal (Caddy handles this automatically)
* Monitor certificate expiration (alert 30 days before expiry)

---

### 3.2 Data at Rest (per REQUIREMENTS.md NFR-4.1, FR-1.4)

**Secrets Encryption:** AES-256 for third-party tokens and credentials

**What Gets Encrypted (field-level):**

* GitHub personal access tokens
* Confluence API tokens (v2)
* Google Docs OAuth tokens (v2)
* Any third-party service credentials

**Storage:**

* Encrypted secrets stored in PostgreSQL `sources` table
* Encryption keys managed via environment-specific secure storage (see 3.2.1)
* Keys MUST NOT be committed to version control

#### 3.2.1 Key storage tiers (required clarity)

* **Enterprise / high assurance:** keys MUST be stored in a secrets manager (AWS Secrets Manager, Vault, etc.).
* **Budget / MVP deployments:** keys MAY be stored in environment configuration only if:

  * `.env` and config files are restricted (e.g., `chmod 600`, owned by service user),
  * host hardening is in place (firewall, minimal users, patched OS),
  * keys are rotated on a defined cadence,
  * access is limited to the minimum required services.

#### 3.2.2 Key Rotation

* Implement key rotation policy (recommended: quarterly)
* Support re-encryption of secrets with new keys
* Document key rotation procedure in runbooks

#### 3.2.3 Database volumes and backups (required)

Even when field-level encryption is limited to secrets, deployments MUST protect persisted storage:

* Production database storage volumes MUST use encryption at rest (cloud volume encryption or equivalent).
* Database backups and snapshots MUST be encrypted at rest.
* Where feasible, deployments SHOULD use customer-managed keys (CMK) for cloud volumes/backups.
* Backups stored in object storage MUST be encrypted server-side and, for enterprise deployments, encrypted with customer-managed keys.
* Access to backup artifacts and any decryption keys MUST be restricted to authorized operators, separated from routine DB credentials where feasible, and audited where possible.
* Database connections SHOULD use TLS where supported (especially across hosts/networks).

#### 3.2.4 Data classification notes (required)

* **Query logs** may contain PII and MUST be protected as sensitive data (access-controlled, retained per policy).
* **Chunk metadata** is access-controlled via RBAC and treated as sensitive operational data.
* **Vector embeddings** are **sensitive derived data** when produced from sensitive documents and MUST be protected by RBAC, environment isolation, and access controls. The system MUST NOT rely on embeddings being “non-sensitive.”

---

## 4. Secrets Management

### 4.1 Connector Credentials (per REQUIREMENTS.md FR-1.4)

**Storage:**

* Third-party tokens encrypted at rest using AES-256
* Keys stored in environment-specific secure storage (secrets manager preferred)

**Access Control:**

* Only ingestion workers can decrypt connector tokens
* Secrets NEVER passed to query/API services
* Use principle of least privilege (each service accesses only required secrets)

**Credential Safety in API Requests (per API.md):**

* `repo_url` in ingestion requests MUST NOT contain embedded credentials
* No `https://token@github.com/repo` patterns allowed
* Return `400 Bad Request` if credentials detected in URL

**Rotation:**

* Rotate GitHub tokens every 90 days
* Implement automated rotation where possible
* Track last rotation date in audit logs

---

### 4.2 Logging Hygiene (per REQUIREMENTS.md FR-1.5, NFR-4.3)

**Hard Rules:**

Sensitive data that MUST NEVER appear in logs:

1. JWT bearer tokens (from `Authorization` headers)
2. Stream tokens (from query strings)
3. Third-party API tokens (GitHub, Confluence)
4. Encryption keys
5. Database passwords
6. PII in raw form (emails, phone numbers, etc.)

**Implementation:**

* Use structured JSON logging with automatic secret redaction
* Redact fields at log emission time (not post-processing)
* Replace secrets with literal `[REDACTED]` marker

**Redaction Patterns (minimum):**

* Bearer tokens: `Authorization: Bearer [REDACTED]`
* JWTs: redact entire token (format: `xxxxx.yyyyy.zzzzz`)
* Query string tokens: `?token=[REDACTED]`
* AWS keys: `AKIA[REDACTED]`
* GitHub tokens: `ghp_[REDACTED]`, `gho_[REDACTED]`

**Log Retention (unified):**

* Operational logs: **14 days** minimum (per NFR-4.3)
* Security audit logs: **1 year** minimum (compliance requirement; see Section 9)
* Implement automated purging after retention period

**Access Control:**

* Restrict log access to authorized operators only
* Implement audit logging for log access (who viewed what, when)

---

## 5. Snippet Sanitization, Redaction & Input Validation

### 5.1 Purpose (per API.md)

Prevent accidental leakage of secrets and PII in query response snippets shown to users, and protect the service from resource exhaustion via input validation.

---

### 5.2 Sanitization Rules (MUST, testable)

**Truncation:**

* Snippets MUST be truncated to `MAX_SNIPPET_CHARS` (default: 500 characters)
* Truncate at word boundaries when possible

**Secret Pattern Redaction (MUST):**

Server MUST redact the following patterns:

1. **Private Key Material:**

   * PEM blocks: `-----BEGIN ... PRIVATE KEY-----` → `[REDACTED]`
   * Entire PEM block removed, not just header

2. **API Keys & Tokens:**

   * JWT-like tokens: `xxxxx.yyyyy.zzzzz` → `[REDACTED]`
   * AWS Access Keys: `AKIA[A-Z0-9]{16}` → `AKIA[REDACTED]`
   * Google API Keys: `AIza[A-Za-z0-9_-]{35}` → `AIza[REDACTED]`
   * Slack Tokens: `xoxb-`, `xoxp-` → `xoxb-[REDACTED]`
   * Generic Bearer tokens: `Bearer [a-zA-Z0-9._-]+` → `Bearer [REDACTED]`

3. **GitHub Tokens:**

   * Personal Access Tokens: `ghp_[A-Za-z0-9]{36}` → `ghp_[REDACTED]`
   * OAuth tokens: `gho_[A-Za-z0-9]{36}` → `gho_[REDACTED]`

**PII Redaction (SHOULD):**

* Email addresses: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` → `[EMAIL_REDACTED]`
* Phone-like patterns: `\+?[0-9]{10,15}` → `[PHONE_REDACTED]`
* SSN-like patterns: `\b\d{3}-\d{2}-\d{4}\b` → `[SSN_REDACTED]`

**Redaction Marker:**

* Use literal string `[REDACTED]` for all secret redactions (consistent, testable)

**Critical Rule:**

* Debug mode (`include_debug=true`) MUST NOT disable sanitization
* Sanitization occurs before response serialization (not optional)

---

### 5.3 Input Validation & Size Limits (required)

To mitigate resource exhaustion and abuse, the API MUST enforce input size and content limits:

* **Maximum JSON body size:** **10 KB**. Requests exceeding this limit MUST return `413 Payload Too Large`.
* **Maximum query text length:** **500 characters** (or configured token length equivalent). Requests exceeding this limit MUST return `400 Bad Request`.
* **Maximum feedback comment length:** **500 characters**; longer comments MUST return `400 Bad Request`.
* Validate content types and reject unexpected content types with `415 Unsupported Media Type`.
* Enforce per-field validation (e.g., expected JSON schema) and return `400 Bad Request` on schema violations.
* Log and monitor `413`, `400`, and other input validation errors as potential attack signals (rate / distribution alerts).

---

### 5.4 Testing Requirements

**Required Tests (per API.md):**

1. JWT patterns redacted correctly
2. AWS access keys redacted
3. PEM blocks completely removed
4. Max length enforced (500 chars) for snippets
5. `[REDACTED]` marker appears in output
6. Debug mode does not bypass sanitization
7. Request body size >10KB returns `413`
8. Query length >500 chars returns `400`
9. Feedback comment >500 chars returns `400`

---

## 6. Query Logs & Privacy

### 6.1 Query Log Storage (per API.md)

**Purpose:** Troubleshooting, feedback analysis, threshold tuning, abuse detection

#### 6.1.0 Production recommendation (required clarity)

Because query text may contain PII, **production deployments SHOULD enable data minimization mode by default** (see 6.1.1).
Storing raw query text SHOULD be limited to explicitly flagged debugging sessions under audit.

**What Gets Logged (default — production recommendation = minimized mode):**

* `query_log_id` (stable identifier)
* User ID (`sub` from JWT) — pseudonymized where possible for non-admin views
* `query_hash` (SHA-256 of normalized query) and `query_length`/token count
* Namespace
* Timestamp
* Latencies (retrieval, generation)
* Top cosine score
* Refusal/success status
* Cost metrics

**Note:** Raw query text is NOT stored by default in production; it is recorded only for explicitly flagged debugging sessions under audited break-glass procedures (see 6.2).

**What Does NOT Get Logged:**

* Full JWT tokens
* Stream tokens
* Connector credentials
* Raw source content

#### 6.1.1 Data minimization mode (recommended option)

Deployments SHOULD support a minimized logging mode to reduce PII risk:

* Store `query_hash` (e.g., SHA-256 of normalized query) and `query_length`/token count
* Store `redacted_query` (optional) where obvious PII patterns are removed
* Store raw query text only for explicitly flagged debugging sessions under audit

---

### 6.2 Privacy Controls

**Retention Policy (per REQUIREMENTS.md NFR-4.5):**

* Query logs and feedback: default **90 days**
* Configurable per deployment
* Automated purging after retention period
* Flagged queries (for evaluation) exempt from auto-purge (require manual approval)

**Access Control:**

* `query_log_id` exposure:

  * **Users:** Only when `include_debug=true` AND only for their own queries
  * **Admins:** Admins MAY access query log metadata for troubleshooting; access MUST be audited
  * **Raw query text access (production default):** MUST require a break-glass workflow and MUST be audited

**Break-glass workflow (required):**

Access to raw query text in production MUST include:

1. Requestor identity (operator/admin `sub`), timestamp, and a required justification string
2. Approval by at least one other authorized security officer or designated approver (automated approvals are permitted only if logged and role-based)
3. Automatic creation of an auditable event including requestor, approver, justification, time window, and `query_log_id`
4. Access granted only for the approved time window (e.g., 1 hour), after which access is revoked and re-request is required
5. Retention of the approval record for at least the audit retention period (**1 year**)

All break-glass events MUST be recorded in the audit log (Section 9) and reviewed periodically.

**Redaction for Non-Privileged Access:**

* If exposing query logs to non-admin UIs, redact:

  * User IDs (show pseudonyms)
  * Query text (show only length/token count or redacted version)
  * Any PII in stored fields

**Right to Deletion:**

* Users may request deletion of their query logs and feedback
* Implement deletion workflow (manual or automated)
* Document deletion procedure in governance docs

---

### 6.3 Feedback Storage (per API.md)

**Data Model:**

* Feedback linked to `query_id` or `query_log_id`
* User ID (`sub`)
* Thumbs up/down (`1` or `-1`)
* Optional comment (max 500 chars)
* Timestamp

**Idempotency:**

* Latest feedback from same user replaces previous feedback for same query
* Prevents duplicate submissions

**Privacy:**

* Feedback comments may contain PII
* Subject to same retention policy as query logs (90 days)
* Honor deletion requests

---

## 7. Transport & Browser Security

### 7.1 CORS Configuration (per API.md)

**When Required:** Cross-origin SSE streaming

**Configuration:**

* Set `Access-Control-Allow-Origin` to specific allowed origins (never `*` in production)
* Expose required headers: `X-RateLimit-*`, `X-Concurrency-*`
* Set `Access-Control-Allow-Credentials: true` only if using cookie auth
* Implement preflight request handling for non-simple requests

**Recommendations:**

* Restrict origins tightly (whitelist only)
* Use environment-specific origin lists (dev vs prod)

---

### 7.2 CSRF Protection (if using cookie auth)

**Required for cookie-based GET streaming:**

* Use `SameSite=Strict` or `SameSite=Lax` cookies
* Implement CSRF token validation (synchronizer token pattern or double-submit cookie)
* Never rely on unauthenticated GET streams

**Not Required for JWT bearer auth** (tokens in Authorization header immune to CSRF)

---

### 7.3 Referrer Policy (per API.md)

**Purpose:** Prevent stream token leakage via Referer header

**Recommended Settings:**

* Set `Referrer-Policy: no-referrer` on streaming responses (strictest)
* Alternative: `Referrer-Policy: strict-origin` (weaker but safer than default)

**Application Guidance:**

* Avoid navigating to third-party origins while tokenized stream URL in browser history/address bar
* Use token-based GET streaming only for same-origin or trusted origins

---

### 7.4 SSE operational security (required)

To prevent leakage and reliability failures in streaming deployments:

* Proxies/load balancers MUST disable response buffering for SSE endpoints (`/api/v1/query` streaming responses and `/api/v1/query/stream`).
* Gateways MUST preserve SSE headers (especially `Content-Type: text/event-stream` and `Cache-Control: no-transform`).
* Operators MUST configure long upstream timeouts suitable for streaming (deployment-defined).
* Deployments SHOULD mitigate reconnect storms by enabling at least one of:

  * `ATTACH_CONCURRENCY_LIMIT`, and/or
  * `ATTACH_RATE_LIMIT_PER_MINUTE`, and/or
  * strict `STREAM_TOKEN_TTL` validation and short retention windows
* Secure response headers SHOULD be enforced on streaming endpoints (e.g., HSTS and other deployment-standard hardened headers).
* Deployments SHOULD monitor attach/reconnect rates and alert on unusually high reconnect rates indicative of reconnect storms or abuse.

---

## 8. Rate Limiting & Cost Protections

### 8.1 Purpose

Prevent abuse, DoS attacks, and cost overruns (per REQUIREMENTS.md FR-5.1)

### 8.2 Limits (per API.md and DECISIONS.md section 11)

**Note:** Rate limit values and policies are maintained in DECISIONS.md (per DECISIONS.md section 11). Implementers MUST consult DECISIONS.md for authoritative, environment-specific values and change history.

**Originating Queries:**

* 50 requests per rolling 1-hour window per user (see DECISIONS.md section 11)
* 5 concurrent active query streams per user

**GET Attachments (by default):**

* Do NOT count toward hourly limit (passive views of existing queries)
* Optional separate limits: `ATTACH_CONCURRENCY_LIMIT`, `ATTACH_RATE_LIMIT_PER_MINUTE`

**Implementation:**

* Redis-based sliding window (sorted set)
* Atomic check-and-increment (Lua script or Redis transaction)
* TTL-based slot cleanup for concurrency tracking

**Cost-counting & budget protection (operational protections):**

* In refusal/degraded modes, `llm_tokens` MUST be zero (no generation). Implementations MUST account for modes where generation is disabled to ensure `llm_tokens` are not billed.
* Budget checks MUST occur **before** generation. Do not begin generation and abort mid-response for budget reasons; prevent start if budget condition would cause abort.
* Optional: meter and alert on anomalous cost patterns (spikes in `llm_tokens` or cost metrics).

**Error Responses:**

* `429 RATE_LIMIT_EXCEEDED`: Hourly limit exceeded
* `429 RATE_LIMIT_CONCURRENCY_EXCEEDED`: Too many concurrent streams
* `429 ATTACH_LIMIT_EXCEEDED`: Attachment limit exceeded (if enabled)

**Headers:**

* `X-RateLimit-Limit`: 50
* `X-RateLimit-Remaining`: count
* `X-RateLimit-Reset`: Unix timestamp (earliest moment when one more request allowed)
* `Retry-After`: seconds until retry allowed

---

## 9. Security Auditability

### 9.1 Audit Events (per REQUIREMENTS.md NFR-4.6)

**What Gets Audited:**

1. **Permission Changes:**

   * Source visibility modifications (`private` → `public`)
   * `allowed_user_ids` updates
   * Role changes (user → admin)

2. **Source Configuration:**

   * Source creation (who, when, which repo)
   * Source deletion (who, when, chunk count)
   * Ingestion triggers (who, when, job ID)

3. **Threshold Changes:**

   * Threshold updates (old value, new value, namespace, who, when)

4. **Admin Actions:**

   * Reindex operations
   * Query log access (including break-glass access)
   * Feedback submitted on behalf of other users (if allowed)

5. **Security Events:**

   * Authentication failures (invalid tokens)
   * Authorization denials (403 Forbidden)
   * Rate limit violations
   * Token revocations (denylist or refresh revocation policy)
   * Key rotation or compromise events (high-severity alerts)

---

### 9.2 Audit Log Format

**Required Fields:**

* `event_type` (string): e.g., `SOURCE_CREATED`, `THRESHOLD_UPDATED`, `AUTH_FAILURE`
* `user_id` (string): Actor (from JWT `sub`)
* `role` (string): Actor's role at event time
* `timestamp` (ISO 8601 UTC)
* `resource_id` (string): e.g., `source_id`, `namespace`
* `details` (object): Event-specific metadata
* `ip_address` (string): Request origin IP
* `user_agent` (string): Client user agent

**Storage:**

* PostgreSQL audit table (separate from operational data)
* Retention: **1 year minimum** (compliance requirement)

**Access Control:**

* Audit logs accessible only by security officers and authorized operators
* Implement audit log access auditing (meta-auditing)

---

## 10. Incident Response

### 10.1 Security Incident Classification

**Critical:**

* Data breach (unauthorized access to user queries or sources)
* Secret exposure (tokens/keys leaked)
* Privilege escalation (user gains admin access)

**High:**

* Authentication bypass
* RBAC violation (user sees unauthorized sources)
* Snippet sanitization failure (secrets in responses)

**Medium:**

* Rate limit bypass
* Query log access by unauthorized users
* Audit log tampering attempts

**Low:**

* Failed authentication attempts (isolated)
* Token expiration errors

---

### 10.2 Response Procedures

**Immediate Actions:**

1. Validate incident (confirm it's not false positive)
2. Contain impact (disable compromised credentials, revoke tokens, rotate signing keys)
3. Notify security officer and incident response team
4. Preserve evidence (logs, database snapshots)

**Investigation:**

1. Determine scope (affected users, data, time range)
2. Root cause analysis (how did it happen?)
3. Identify indicators of compromise (IOCs)

**Remediation:**

1. Patch vulnerability
2. Rotate compromised credentials and signing keys
3. Invalidate affected sessions/tokens (denylist or refresh revocation)
4. Notify affected users (if data breach)

**Post-Incident:**

1. Document incident in postmortem (per REQUIREMENTS.md NFR-3.6)
2. Update runbooks with lessons learned
3. Implement preventive controls

---

## 11. Compliance & Testing

### 11.1 Required Security Tests (per API.md)

(See API.md / test plans for full test matrix.)

### 11.2 Security Scanning

(See CI policies / scanning runbooks.)

---

## 12. Supply Chain & CI/CD Security (Required)

### 12.1 Build integrity requirements (required)

* CI/CD runners MUST use least-privileged credentials (scoped tokens, minimal repository permissions).
* Builds SHOULD pin base images by immutable digest where feasible.
* Deployments SHOULD generate and retain an SBOM (software bill of materials) per release.
* Secrets scanning MUST run in CI (and pre-commit where practical).
* Release artifacts SHOULD be signed (or otherwise integrity-protected) for production deployments.
* Branch protection SHOULD be enforced (required reviews, required CI green) for production-bound branches.
* CI/CD tokens SHOULD be short-lived and rotated regularly.

### 12.2 Dependency governance (required)

* Direct dependencies SHOULD be pinned to known-good versions.
* Critical vulnerabilities MUST be patched or mitigated within 7 days (per scanning policy).
* Dependency changes SHOULD be reviewed (PR approvals) and audited.

---

## 13. Configuration Checklist

### 13.1 Production Deployment Checklist

**Authentication:**

* [ ] JWT signing configured (allowed algorithms explicitly set; no `alg=none`)
* [ ] JWT validation includes `iss` + `aud` + `exp` (+ optional `nbf`) with explicit clock skew
* [ ] `kid` required; verification key set managed; internal JWKS distribution and refresh behavior defined
* [ ] JWT signing key secure (256-bit minimum for HS256; protected private key for RS/ES)
* [ ] JWT signing keys protected via KMS/HSM where feasible (enterprise recommended)
* [ ] Token expiration enforced (1 hour for users, 15 min for admins)
* [ ] Token revocation strategy documented (TTL-only + refresh, or denylist) and enforced at all verification points
* [ ] Stream token TTL set to 60 seconds
* [ ] Idempotency-Key support implemented for cost-sensitive endpoints (24h retention, user-scoped)

**Encryption:**

* [ ] TLS 1.3 enabled on all external endpoints
* [ ] TLS certificate valid and auto-renewal configured
* [ ] AES-256 field-level encryption enabled for secrets in database
* [ ] DB volumes and backups encrypted at rest (CMK where feasible)
* [ ] DB connections use TLS where supported (especially cross-host)
* [ ] Key storage matches deployment tier:

  * [ ] Enterprise: secrets manager (preferred)
  * [ ] Budget/MVP: locked-down env files + host hardening + rotation cadence

**RBAC:**

* [ ] RBAC enforcement enabled in vector search metadata filters
* [ ] Default visibility set to `private`
* [ ] Admin bypass (if any) is explicit and auditable; limited to diagnostic source visibility and must not bypass user RBAC

**Streaming (SSE):**

* [ ] Proxy buffering disabled for SSE endpoints
* [ ] Long upstream timeouts configured for streams
* [ ] Query string logging disabled/redacted for `/api/v1/query/stream`
* [ ] Attach storm controls enabled if needed (`ATTACH_*` and/or strict TTL)
* [ ] Streaming endpoints protected with hardened security headers (deployment standard)

**Input Validation & Limits:**

* [ ] Max JSON body: 10 KB enforced (HTTP 413)
* [ ] Max query length: 500 chars enforced (HTTP 400)
* [ ] Max feedback comment length: 500 chars enforced (HTTP 400)

**Logging & Retention:**

* [ ] Secret redaction enabled in logging configuration
* [ ] Audit logging enabled for all security events
* [ ] Query logs + feedback retention: 90 days (configurable) — minimized logging enabled by default in production
* [ ] Operational logs retention: 14 days
* [ ] Audit logs retention: 1 year
* [ ] Break-glass workflow required and audited for raw query text access in production

**Rate Limiting & Cost Protections:**

* [ ] Redis configured for rate limiter
* [ ] Hourly limit set to 50 requests/user (confirm in DECISIONS.md section 11)
* [ ] Concurrency limit set to 5 streams/user
* [ ] Budget checks before generation; `llm_tokens` zero in refusal/degraded modes

**Monitoring:**

* [ ] Alerts configured for authentication failures
* [ ] Alerts configured for rate limit violations
* [ ] Certificate expiration monitoring (30 days)
* [ ] Snippet sanitization failure alerts
* [ ] Alerts configured for key compromise/rotation events
* [ ] Alerts configured for unusual attach/reconnect storms (if enabled)

**Supply Chain:**

* [ ] CI secrets scanning enabled
* [ ] Base images pinned (digest) where feasible
* [ ] SBOM generated per release (recommended)
* [ ] Release artifact integrity controls in place (signing recommended)
* [ ] Branch protection enabled for production-bound branches

---

## 14. Related Documents

* [Architecture](../../Backbond/ARCHITECTURE.md) — System architecture with security invariants
* [Requirements](../../Backbond/REQUIREMENTS.md) — Functional and non-functional security requirements (FR-1.x, NFR-4.x)
* [API Documentation](../02_api/API.md) — API security contracts and error handling
* [Data Governance](../08_governance/DATA_GOVERNANCE.md) — PII handling and retention policies
* [Operations](../../Backbond/OPERATIONS.md) — Security monitoring and incident response procedures
* **Authoritative rate-limits and environment-specific decisions:** DECISIONS.md section 11 (see referenced file for change history and canonical values)

> Note: links reference `Backbone` as the canonical folder name. If your repository uses another path, update links accordingly.

---

## Version History

| Version | Date       | Changes                                                                                                                                                                                                                                                                                    |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| v1.0    | 2026-03-11 | Initial production security documentation based on REQUIREMENTS v1.5, ARCHITECTURE v1.6, API v1.0.10                                                                                                                                                                                       |
| v1.0.1  | 2026-03-11 | Clarified data classification (embeddings), unified retention, added JWT alg/rotation/revocation, added env isolation + service boundaries, aligned checklist                                                                                                                              |
| v1.0.2  | 2026-03-11 | Added JWT `iss`/`aud` validation, `kid` + key rotation requirements, tightened admin raw query access (break-glass default), added SSE operational hardening, added DB volume/backup encryption, added CI/CD & supply-chain security requirements                                          |
| v1.0.3  | 2026-03-11 | Made minimized logging the production-default “what gets logged”, added JWKS distribution/refresh requirements, clarified KMS/HSM guidance for signing keys, strengthened break-glass workflow requirements, added CMK guidance for backups, and added key compromise alerting requirement |
| v1.0.4  | 2026-03-11 | Added Idempotency-Key requirements, input validation (size limits), DECISIONS.md reference for rate limits, clarified admin bypass diagnostic scope (no RBAC bypass for user queries), added cost/budget protection notes, and minor consistency fixes                                     |

