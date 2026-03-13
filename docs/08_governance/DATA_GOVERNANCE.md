# Data Governance Documentation

**Version:** v1.1
**Status:** Production Data Governance Policies
**Last Updated:** 2026-03-11
**Compliance:** REQUIREMENTS.md v1.5 (NFR-4.x), SECURITY.md v1.0.4, GDPR/CCPA principles

> This document defines data governance policies, data classification, retention rules, PII handling, access controls, deletion rights, and compliance requirements for the Smart Office Librarian RAG system.
> **Canonical additions in v1.1:** Systems of Record, Chunk Text Storage Policy, Permission Revocation Rules, Backup Deletion Semantics, and explicit deletion/legal hold schema fields.

---

## Overview

Data governance ensures that all data collected, stored, and processed by the Smart Office Librarian is handled responsibly, securely, and in compliance with privacy regulations. This document establishes policies for:

* **Data Classification:** Categorizing data by sensitivity level
* **PII Handling:** Identifying, protecting, and minimizing personally identifiable information
* **Retention Policies:** Defining how long different data types are stored
* **Access Controls:** Restricting data access to authorized personnel only
* **Deletion Rights:** Honoring user requests for data deletion
* **Compliance:** Meeting regulatory requirements (GDPR, CCPA principles)

**Governance Principles:**

* **Data Minimization:** Collect only what is necessary for system operation
* **Purpose Limitation:** Use data only for stated purposes
* **Transparency:** Users understand what data is collected and why
* **User Rights:** Users can access, correct, and delete their data
* **Accountability:** Clear ownership and audit trails for data handling

---

## 0. Systems of Record & Data Flow (Canonical)

This section defines **where data lives** and what systems are considered authoritative.

### 0.1 Systems of Record (Canonical)

**PostgreSQL (System of Record):**

* Users, roles, and authentication metadata
* Sources and index metadata (namespace, model_id, index_version, last_indexed_sha)
* Chunk metadata (file path, line ranges, chunk hashes, ingest_run_id)
* Query logs and feedback
* Thresholds
* Audit logs and break-glass approvals
* Ingest runs

**Vector DB (Derived Index, Rebuildable):**

* Stores **vector embeddings** and **minimal metadata** needed for filtering and lookup.
* Must be rebuildable from:

  * source repositories (GitHub/Confluence/Docs) + ingestion pipeline, and
  * Postgres source configuration and chunk metadata.

**Redis (Ephemeral / Non-System-of-Record):**

* Rate limit counters and concurrency counters (TTL-based)
* Embedding cache (TTL 24h)
* Retrieval cache (TTL 60s)
* Worker heartbeats (TTL 90s)
* Redis must **not** store raw credentials, raw document content, or raw query text.

### 0.2 Data Flow Summary

1. Ingestion reads repository content → chunks text → creates embeddings.
2. Vector DB stores embeddings + metadata + `chunk_id`.
3. PostgreSQL stores chunk metadata and (optionally) chunk text (see Section 0.3).
4. Query path retrieves candidate chunk IDs from vector DB → loads snippets from PostgreSQL → generates cited answer (or refusal).

### 0.3 Chunk Text Storage Policy (Canonical)

**Canonical v1 policy (required):**
✅ **Chunk text is stored in PostgreSQL** (chunks table) and **NOT stored in Vector DB**.

**Vector DB stores:**

* embedding vector
* `chunk_id`
* RBAC metadata (visibility, allowed_user_ids)
* source metadata required for filtering (repo, file_path, commit_sha, start_line, end_line, model_id, index_version, ingest_run_id, chunk_hash)

**Why (governance + security):**

* Keeps raw document content in the system-of-record with stronger governance controls.
* Minimizes exposure surface area with third-party vector providers.
* Makes deletion, legal holds, and auditing more consistent.

---

## 1. Data Classification

### 1.1 Classification Levels

**Critical / Highly Sensitive:**

* Third-party API tokens and credentials (GitHub PATs, OAuth tokens)
* Encryption keys and signing keys
* Database passwords and connection strings
* JWT signing keys

**Sensitive:**

* Raw query text (may contain PII or confidential information)
* User email addresses and contact information
* Query logs with user identifiers
* Feedback comments (may contain PII)
* Source document content (private/confidential documents)
* Vector embeddings derived from sensitive sources (derived sensitive data)
* Chunk text stored in PostgreSQL (source-derived content)

**Internal / Operational:**

* Query hashes (SHA-256, pseudonymized)
* Aggregated metrics and analytics
* System logs (redacted)
* Performance metrics
* Error logs (sanitized)
* Redis counters (rate limits, concurrency) (ephemeral)

**Public:**

* Documentation and API specifications
* Public repository content (where `visibility=public`)
* Aggregated, anonymized statistics

### 1.2 Handling Requirements by Classification

| Classification Level | Encryption at Rest   | Encryption in Transit | Access Controls           | Audit Logging | Retention Policy                      |
| -------------------- | -------------------- | --------------------- | ------------------------- | ------------- | ------------------------------------- |
| Critical             | AES-256 (required)   | TLS 1.3 (required)    | Admin only                | Required      | Per rotation policy                   |
| Sensitive            | DB volume encryption | TLS 1.3 (required)    | Role-based + need-to-know | Required      | 90 days default (varies by data type) |
| Internal             | DB volume encryption | TLS 1.3 (required)    | Authenticated users       | Optional      | 14–90 days                            |
| Public               | Not required         | TLS 1.3 (recommended) | Public or authenticated   | Not required  | Indefinite                            |

---

## 2. Personally Identifiable Information (PII)

### 2.1 PII Definition

PII includes but is not limited to:

* Email addresses
* Full names (when combined with other identifiers)
* Phone numbers
* IP addresses (in some jurisdictions)
* User IDs directly linkable to real identities
* Location data
* Any content in queries or feedback that reveals personal information

### 2.2 PII Minimization Strategy

**Collection:**

* Collect only `sub` (user ID), `role`, and `exp` from JWT claims for operational purposes.
* Do NOT store user emails in query logs unless explicitly required for account workflows.
* Use pseudonymous identifiers (`sub`) rather than real names where possible.

**Storage:**

* **Query text (PII risk):** By default, store only:

  * `query_hash` (SHA-256)
  * `query_length`
  * timestamps and metrics
* **Raw query text storage:** Permitted only for explicitly flagged debugging sessions under break-glass controls (SECURITY.md Section 6).
* **Feedback comments:** max 500 characters; treated as sensitive; 90-day retention default.

**Processing:**

* Redact PII patterns before:

  * writing logs,
  * saving debug query text,
  * returning source snippets to UI,
  * returning sanitized error messages.
* Never log Authorization headers, stream tokens, or query string tokens.
* Pseudonymize user IDs in non-admin analytics and dashboards.

### 2.3 PII Redaction Patterns (Required)

**PII_REDACTION_VERSION:** `v1`

Automated redaction MUST be applied to logs and snippets for:

* Email addresses → `[EMAIL_REDACTED]`
* Phone numbers → `[PHONE_REDACTED]`
* SSN-like patterns → `[SSN_REDACTED]`
* IP addresses → `[IP_REDACTED]` (enable if required by jurisdiction)

**Where redaction runs (Canonical):**

* Logging formatter / structured logger (server-side)
* Snippet renderer (before sending snippets to frontend)
* Error serializer (before returning messages to clients)

### 2.4 PII in Vector Embeddings (Derived Sensitive Data)

**Risk:** Embeddings derived from documents containing PII are sensitive derived data.

**Controls:**

* Enforce RBAC at vector search time via metadata filters.
* Do NOT share embeddings across users with different access levels.
* Treat embeddings as sensitive operational data requiring access controls and environment isolation.
* Embeddings MUST NOT be publicly exposed, exported, or shared outside the system.

---

## 3. Data Retention Policies

### 3.1 Retention Schedule (Canonical)

| Data Type                        | Default Retention                            | Rationale                          | Exception Process                                               |
| -------------------------------- | -------------------------------------------- | ---------------------------------- | --------------------------------------------------------------- |
| **Query logs**                   | 90 days                                      | NFR-4.5                            | Flagging for evaluation requires approval; legal hold overrides |
| **Feedback (thumbs/comments)**   | 90 days                                      | Linked to query logs               | Flagging for tuning requires approval; legal hold overrides     |
| **Operational logs**             | 14 days                                      | NFR-4.3                            | Critical incidents may extend retention (documented)            |
| **Audit logs**                   | 1 year minimum                               | NFR-4.6                            | Security/legal hold may require longer retention                |
| **Source metadata**              | Until source deleted                         | Operational necessity              | N/A                                                             |
| **Chunk metadata + chunk text**  | Until source deleted or reindexed            | Needed for citations and retrieval | Purged on source deletion and reindex lifecycle                 |
| **Vector embeddings**            | Until source deleted or reindexed            | Derived index                      | Purged on source deletion, rename purge, or reindex swap        |
| **User credentials (encrypted)** | Until user deactivated or credential rotated | Ingestion continuity               | Rotated every 90 days per SECURITY.md                           |
| **Encryption keys**              | Per rotation policy (quarterly)              | Security                           | Emergency rotation may shorten grace                            |

### 3.2 Retention Enforcement

**Automated purging (Required):**

* Scheduled purge jobs MUST run at least daily.
* Query logs and feedback older than 90 days MUST be deleted unless:

  * `is_flagged=true` and approved, or
  * `legal_hold=true`.
* Operational logs older than 14 days MUST be deleted (unless legal hold for incident).
* Audit logs older than 1 year may be purged **only if** not under legal hold.

**Soft delete + purge (Canonical):**

* Immediate: soft-delete record (set `is_deleted=true`, `deleted_at=now`, `purge_after=now+7..14d`)
* Later: hard-delete after grace period, unless legal hold.

### 3.3 Canonical Deletion / Retention Schema Fields (Required)

All relevant tables (query logs, feedback, and any user-scoped data) MUST implement:

* `is_deleted: bool`
* `deleted_at: timestamp`
* `purge_after: timestamp`

For retention exceptions:

* `is_flagged: bool`
* `flag_reason: text`
* `flagged_by: user_id`
* `flagged_at: timestamp`
* `flag_expires_at: timestamp (optional)`

For legal holds:

* `legal_hold: bool`
* `legal_hold_reason: text`
* `legal_hold_set_by: user_id`
* `legal_hold_at: timestamp`

### 3.4 Manual Exemptions

Flagging a query/feedback for evaluation exempts it from auto-purge only if:

* documented reason,
* approver recorded,
* duration specified,
* reviewed quarterly.

### 3.5 Backup Deletion Semantics (Canonical)

**Backups are immutable and time-limited.**

* PostgreSQL backups retained **7 days minimum** (per REQUIREMENTS/NFR target).
* Deleted data may remain in backups until backup retention expires.
* This behavior MUST be disclosed in the privacy policy and deletion workflow documentation.

---

## 4. Access Control & Authorization

### 4.1 Access Levels (Canonical)

**Public Data:**

* Content where `visibility=public`
* Accessible by authenticated users (and optionally public endpoints if product chooses)
* No additional authorization beyond authentication

**Private Data:**

* Content where `visibility=private` and `allowed_user_ids` includes user
* Enforced at vector search metadata filter (ARCHITECTURE.md Invariant D)

**User-Scoped Data:**

* User’s own query logs (when debug is enabled)
* User’s own feedback
* Accessible only by the creator, or admins **with audit logging**

**Admin-Only Data:**

* Aggregated query metrics across all users
* Source configuration + ingestion controls
* Threshold tuning and system settings
* Audit logs and security events
* Admin access MUST be audited (SECURITY.md Section 9)

**Break-Glass Access (Highly Restricted):**

* Raw query text in production (default: not stored)
* Requires:

  * justification,
  * approver,
  * time-limited access (1 hour),
  * full audit event with scope and window.

### 4.2 Canonical RBAC Enforcement Rules (Required)

* Retrieval filter MUST enforce:

  `(visibility == "public") OR (allowed_user_ids $in [current_user.id])`

* RBAC must apply at:

  * vector retrieval time (metadata filter),
  * snippet loading time (Postgres fetch must re-check user scope by chunk’s source permissions).

### 4.3 Permission Sync, Revocation, and Reconciliation (Canonical)

**Authoritative source:**

* For GitHub: repository access lists / team membership are authoritative.

**Sync triggers:**

* Scheduled sync at minimum daily (MVP).
* Optional webhook-based sync for near-real-time changes (v2).

**Revocation SLA (Canonical target):**

* Permission changes must take effect within **24 hours** (MVP scheduled sync).
* In v2 with webhooks, target within minutes.

**Revocation behavior (Required):**

* If a user loses access to a source:

  * they must no longer retrieve any chunks from that source (RBAC filter prevents it),
  * cached retrieval results must not bypass RBAC (cache keys must include RBAC scope).

**Admin override:**

* Admin role does not automatically grant access to all private content unless explicitly configured.
* Emergency access is via break-glass, audited.

### 4.4 Data Access Audit Requirements

All access to sensitive data MUST be auditable:

* **Who:** user ID (`sub`) and role
* **What:** data type and resource ID accessed
* **When:** timestamp (ISO 8601 UTC)
* **Why:** justification (required for break-glass)
* **Result:** success or denial
* **Duration:** time window (if applicable)

Audit logs retained 1 year minimum.

---

## 5. Third-Party & Vendor Data Handling

### 5.1 Prohibited Third-Party Access

* No third-party service providers may have direct access to:

  * user query logs,
  * feedback,
  * raw queries,
  * raw source documents,
  * audit logs,
    unless explicitly approved and covered by DPAs and security review.

### 5.2 Permitted Third-Party Processing (with controls)

* **OpenAI API:** receives query text and context chunks needed for generation.
  Controls:

  * apply redaction where feasible,
  * do not log provider payloads containing sensitive content,
  * comply with DPAs and security configuration.

* **Vector DB provider:** stores embeddings and metadata only; chunk text remains in PostgreSQL.
  Controls:

  * RBAC metadata stored with vectors,
  * no public exposure.

* **Redis:** ephemeral keys and counters only.

### 5.3 Vendor Audit

* Review DPAs annually.
* Document data flows and subprocessors.

---

## 6. User Data Rights

### 6.1 Right to Access

Users may request access to their own data within 30 days.

**Provided data (portable JSON/CSV):**

* query logs (hashes, timestamps, refusal status, costs/latencies)
* feedback (thumbs/comments, timestamps)
* list of sources accessed (subject to RBAC)

**Not provided:**

* embeddings (derived data),
* audit logs of admin actions (unless legally required).

### 6.2 Right to Rectification (Canonical with immutable logs)

* Query logs are immutable: they cannot be edited.
* Rectification is handled by:

  * adding a correction record (audit event),
  * marking feedback as “superseded” rather than overwriting (retain original for compliance).

### 6.3 Right to Deletion (“Right to be Forgotten”)

**User-initiated deletion applies to:**

* query logs associated with user `sub`
* feedback submitted by user
* cached data (invalidate Redis entries)
* optional reset of rate limiting counters

**Process:**

1. Soft-delete immediately
2. Hard-delete after 7–14 days grace
3. Backups expire after retention window (Section 3.5)

**Limitations:**

* audit logs retained 1 year minimum
* aggregated anonymized metrics may remain
* indexed organizational documents are not “user data” (separate retention policy)

**Exceptions:**

* legal holds
* security investigations
* compliance obligations with documented justification

### 6.4 Right to Data Portability

* Export format: JSON and CSV
* Excludes: embeddings, audit logs, internal-only identifiers

---

## 7. Compliance Requirements

### 7.1 GDPR Principles (EU Users)

* Lawful basis: legitimate interest (system operation, security); consent for optional feedback comments if needed
* Data subject rights covered in Section 6
* DPO appointment if required by scale
* International transfers must use SCCs or equivalent mechanisms

### 7.2 CCPA Principles (California Users)

* transparency on categories collected + retention periods
* deletion and opt-out rights (no sale of data)
* service providers operate under DPAs

### 7.3 Breach Notification

* follow SECURITY.md incident response
* notify affected users within 72 hours of discovery where required
* include breach nature, impacted data, remediation steps, contact info

---

## 8. Data Processing Agreements (DPAs)

### 8.1 Required DPAs

* OpenAI (LLM/embeddings)
* Vector DB provider
* Cloud provider (hosting/storage)

### 8.2 DPA Review Cycle

* annual review
* update when vendors or terms change
* track DPA status in compliance checklist

---

## 9. Governance Operating Model

### 9.1 Roles & Responsibilities

**Data Governance Officer:**

* approves retention exemptions
* coordinates DPA reviews
* oversees compliance

**Security Officer:**

* manages break-glass approvals
* monitors anomalies
* leads incident response with governance officer

**Engineering Lead:**

* implements controls (purge jobs, encryption, RBAC, redaction)
* documents data flows

**Admins:**

* manage ingestion/thresholds with audit logging
* process user access/deletion requests

### 9.2 Policy Review & Updates

* annual review or upon major architecture/regulatory changes
* update version history and notify stakeholders

### 9.3 Training & Awareness

* annual training required for operators/admins
* covers PII handling, break-glass, retention, incident response

---

## 10. Compliance Checklist

### 10.1 Implementation Checklist

**Data Minimization**

* [ ] Production stores query hashes (not raw queries) by default
* [ ] PII redaction implemented for logs/snippets/errors (PII_REDACTION_VERSION v1)
* [ ] Feedback comments limited to 500 characters
* [ ] Only necessary JWT claims (`sub`, `role`, `exp`) collected

**Retention Enforcement**

* [ ] Purge jobs configured and tested (90d logs/feedback, 14d ops logs, 1y audit logs)
* [ ] Canonical schema fields implemented (`is_deleted`, `purge_after`, `legal_hold`, `is_flagged`)
* [ ] Exemption approval workflow documented
* [ ] Legal hold workflow documented and tested

**Access Controls**

* [ ] RBAC enforced at vector search and Postgres snippet load
* [ ] Admin actions audited
* [ ] Break-glass workflow implemented for raw query text
* [ ] Permission sync and revocation rules implemented (SLA ≤ 24h for MVP)

**User Rights**

* [ ] Data access export (JSON/CSV) implemented
* [ ] Deletion workflow implemented (soft + hard + backup semantics disclosed)
* [ ] Privacy policy published

**Compliance**

* [ ] DPAs signed (OpenAI, vector DB, cloud)
* [ ] Breach notification runbook tested

**Encryption & Security**

* [ ] TLS 1.3 on external endpoints
* [ ] AES-256 encryption for secrets at rest
* [ ] DB volume + backup encryption enabled
* [ ] No secrets in logs/errors/telemetry

### 10.2 Audit & Testing

**Quarterly**

* [ ] Review access logs for anomalies
* [ ] Verify retention (data volumes by age)
* [ ] Test deletion workflow end-to-end
* [ ] Review flagged exemptions and confirm justification

**Annual**

* [ ] Compliance review against GDPR/CCPA principles
* [ ] Annual DPA review
* [ ] Policy update + version bump
* [ ] Training completion verification

---

## 11. Related Documents

* [Security Documentation](../04_security/SECURITY.md) — Authentication, RBAC, encryption, audit logging
* [Requirements](../../Backbond/REQUIREMENTS.md) — NFR-4.x security and privacy requirements
* [API Documentation](../02_api/API.md) — Query logging, feedback, data exposure policies
* [Operations](../../Backbond/OPERATIONS.md) — Incident response, monitoring, runbooks
* [Decisions](../../Backbond/DECISIONS.md) — Canonical rate limits, RBAC filter semantics, caching policies
* [Architecture](../../Backbond/ARCHITECTURE.md) — Invariant D (RBAC), Systems of Record, metadata contracts

---
