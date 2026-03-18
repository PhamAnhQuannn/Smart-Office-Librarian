# Data Lifecycle Policy — v1.0

**Last Updated:** 2026-01-01  
**Owner:** Engineering / Data Governance

---

## Overview

This document defines retention, archival, and deletion policies for all data stored and processed by Embedlyzer.

---

## Data categories

| Category | Storage | Retention | Deletion method |
|----------|---------|-----------|----------------|
| User accounts | PostgreSQL `users` | Indefinite while active; 30 days after deactivation | Hard delete via admin API |
| Query logs | PostgreSQL `query_logs` | 90 days | Automated purge job |
| Feedback | PostgreSQL `feedbacks` | 180 days | Automated purge job |
| Ingest run records | PostgreSQL `ingest_runs` | 365 days | Automated purge job |
| Evaluation results | PostgreSQL `evaluation_results` | 365 days | Manual archival |
| Audit logs | PostgreSQL `audit_logs` | 7 years (compliance) | Archival to cold storage after 1 year |
| Source chunks (vectors) | Pinecone | Active namespace: indefinite; deleted source: immediate | `delete` API call on source delete |
| Source metadata | PostgreSQL `chunks` | Synchronized with Pinecone; cascade-deleted with source | Cascade delete |
| Backups | Object storage (S3/GCS) | 30 daily, 12 monthly | Automated lifecycle rule |
| Application logs | Docker / Loki | 14 days rolling | Log rotation |

---

## Automated retention jobs

### Query log purge
Runs daily at 02:00 UTC:
```sql
DELETE FROM query_logs WHERE created_at < now() - interval '90 days';
```

### Feedback purge
Runs weekly at 03:00 UTC:
```sql
DELETE FROM feedbacks WHERE created_at < now() - interval '180 days';
```

### Ingest run purge
Runs monthly on the 1st at 04:00 UTC:
```sql
DELETE FROM ingest_runs WHERE created_at < now() - interval '365 days';
```

---

## Right to erasure (GDPR Art. 17)

When a user requests deletion:
1. Deactivate account: `PATCH /api/v1/admin/users/{id}` `{"is_active": false}`
2. Purge user data within 30 days:
   - Delete `query_logs` rows for `user_id`.
   - Anonymize `feedbacks` rows (set `user_id = NULL`).
   - Delete `user_namespace_grants` rows.
   - Hard-delete the `users` row.
3. Log the erasure event in `audit_logs` with `action="user_erasure_completed"`.
4. Confirm to the user in writing within 30 days.

---

## Source data deletion

When a source is deleted via `DELETE /api/v1/sources/{id}`:
1. Pinecone vectors for that `source_id` are deleted (namespace-scoped).
2. `chunks` rows are cascade-deleted from PostgreSQL.
3. `sources` row is deleted.
4. The associated ingest run records are retained per the ingest run retention policy.

---

## Backup lifecycle

Automated backups run via `backend/scripts/backup_db.sh`:
- **Daily backups:** retained for 30 days.
- **Monthly backups:** retained for 12 months.
- Backups are encrypted with AES-256 at rest.
- See `DEPLOYMENT.md` for restore procedure.

---

## Data classification

| Class | Examples | Controls |
|-------|---------|---------|
| Public | Documentation content from public repos | No special controls |
| Internal | Private repo source code chunks | RBAC namespace grants; encrypted at rest |
| Confidential | User credentials (hashed), JWT secrets | bcrypt hashing; secrets in Vault/env; audit logged |
| Sensitive PII | User email addresses | Access restricted to admin; included in erasure scope |
