# Runbook: Disk Full

**Alert:** `DiskSpaceCritical` (> 95%) / `DiskSpaceWarning` (> 80%)  
**Severity:** critical / warning  
**Last Updated:** 2026-01-01

---

## Symptoms

- Disk usage alert fires.
- PostgreSQL write errors: `could not extend file: No space left on device`.
- Docker log writes failing.

---

## Immediate triage

```bash
# Check disk usage on host
df -h

# Find largest directories
du -sh /* 2>/dev/null | sort -rh | head -20
du -sh /var/lib/docker/* 2>/dev/null | sort -rh | head -10
```

---

## Common causes and fixes

### 1. Docker logs accumulated

```bash
# Show container log file sizes
du -sh /var/lib/docker/containers/*/*.log 2>/dev/null | sort -rh | head -10

# Truncate a specific container's log (safe — Docker recreates it)
truncate -s 0 /var/lib/docker/containers/<id>/<id>-json.log
```

Prevent recurrence — add log rotation to `docker-compose.yml`:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "3"
```

### 2. PostgreSQL WAL files

```bash
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"

# Check WAL directory size
du -sh /var/lib/docker/volumes/embedlyzer_postgres_data/_data/pg_wal/
```

- Run `VACUUM FULL` on large tables.
- Check that `wal_keep_size` isn't set excessively in `postgresql.conf`.

### 3. Pinecone backup or evaluation result files

```bash
du -sh /app/evaluation/results/
ls -lth /app/evaluation/results/ | head -20
```

Remove old result files:
```bash
find /app/evaluation/results/ -name '*.json' -mtime +30 -delete
```

### 4. Unused Docker images/volumes

```bash
docker system df
docker system prune -f           # removes stopped containers, dangling images
docker volume prune -f           # removes unused volumes (CAREFUL in production)
```

---

## Emergency disk recovery (critical)

If Postgres has stopped writing due to disk full:
1. Free space immediately (truncate logs, remove old files).
2. Restart Postgres: `docker compose restart postgres`
3. Verify database health: `psql $DATABASE_URL -c "SELECT 1;"`

---

## Escalation

If disk cannot be freed quickly:
1. Open SEV-2 incident.
2. Request infrastructure team to expand volume.
3. Put ingestion in manual hold to prevent further writes until resolved.
