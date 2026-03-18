# Runbook: Pinecone Index Mismatch

**Alert:** `IndexMismatch` (custom application alert)  
**Severity:** warning  
**Last Updated:** 2026-01-01

---

## Symptoms

- Query results contain citations for deleted/re-ingested files.
- Vector count in Pinecone does not match chunk count in PostgreSQL.
- Queries return stale content after source files were updated.
- Ingest run completed successfully but old chunks are still appearing.

---

## Immediate triage

```bash
# Count chunks in Postgres
psql $DATABASE_URL -c "SELECT namespace, count(*) FROM chunks GROUP BY namespace;"

# Count vectors in Pinecone (via describe_index_stats)
curl -s "https://controller.<env>.pinecone.io/databases/<index>/describe_index_stats" \
  -H "Api-Key: $PINECONE_API_KEY" | jq '.namespaces'
```

---

## Common causes and fixes

### 1. Failed partial ingestion (crash mid-run)

An ingest run partially completed — some old vectors were purged, new ones not yet upserted.

```bash
# Find failed or partial runs
psql $DATABASE_URL -c "
  SELECT id, repo, branch, status, ingested_documents, error_message, started_at
  FROM ingest_runs
  WHERE status IN ('failed', 'running')
  ORDER BY started_at DESC LIMIT 10;"
```

Re-trigger ingestion with force re-ingest:
```bash
curl -s -X POST http://localhost:8000/api/v1/ingest \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repo": "<repo>", "branch": "main", "force_reingest": true}'
```

### 2. Manual Pinecone deletion without DB sync

If vectors were deleted directly in Pinecone without updating the `chunks` table:

```bash
# Delete orphan chunk records for a namespace
psql $DATABASE_URL -c "DELETE FROM chunks WHERE namespace = '<ns>';"
```

Then re-ingest all sources:
```bash
python scripts/migrate_index.py \
  --src-index embedlyzer --dst-index embedlyzer \
  --src-namespace default --dst-namespace default \
  --re-embed
```

### 3. Namespace mismatch (env variable changed)

If `PINECONE_NAMESPACE` was changed after data was ingested, existing vectors are in the old namespace.

- Use `migrate_index.py` to copy/re-embed vectors into the new namespace.
- Update all query requests to use the new namespace.

### 4. Index version bump without migration

After an embedding model upgrade, vectors in the index are from the old model.

```bash
python scripts/migrate_index.py \
  --src-index embedlyzer-v1 --dst-index embedlyzer-v2 \
  --re-embed
```

---

## Verification

After re-ingestion:
```bash
# Run golden questions evaluation to verify quality
python evaluation/scripts/evaluate_golden_questions.py \
  --dataset evaluation/datasets/golden_questions_v1.json \
  --output evaluation/results/post-reindex.json
```

---

## Escalation

If mismatch persists after forced re-ingest:
1. Open SEV-2 incident.
2. Take a Postgres backup: `bash backend/scripts/backup_db.sh`
3. Contact Pinecone support if index state appears corrupted.
