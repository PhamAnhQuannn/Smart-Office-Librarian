# Runbook: Database Connection Pool Exhausted

**Alert:** `DBConnectionPoolExhausted`  
**Severity:** critical  
**Last Updated:** 2026-01-01

---

## Symptoms

- `embedlyzer_db_pool_wait_ms_p95` > 500 ms.
- 503 / 500 errors from endpoints that query the database.
- Logs show `TimeoutError: QueuePool limit of size X overflow Y reached`.

---

## Immediate triage

```bash
# Check pool wait time in logs
docker logs embedlyzer-api --since=5m | grep 'pool'

# Check active DB connections
psql $DATABASE_URL -c "
  SELECT count(*), state, wait_event_type, wait_event
  FROM pg_stat_activity
  WHERE datname = current_database()
  GROUP BY state, wait_event_type, wait_event
  ORDER BY count DESC;"
```

---

## Common causes and fixes

### 1. Leaked connections (long-running transactions)

```sql
SELECT pid, now() - xact_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
  AND xact_start < now() - interval '30 seconds'
ORDER BY duration DESC;
```

Terminate hanging connections:
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND xact_start < now() - interval '5 minutes';
```

### 2. Pool size too small for load

Increase pool settings in `.env`:
```
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

Restart the API to apply:
```bash
docker compose restart api
```

### 3. Too many API replicas sharing a small pool

Each replica holds up to `pool_size + max_overflow` connections.  
If running 3 replicas with `pool_size=10`, Postgres needs to accept 90 connections total.

Check `max_connections` in Postgres:
```sql
SHOW max_connections;
```

Increase via `postgresql.conf` or use PgBouncer as a connection pooler.

### 4. Worker holding connections

Celery tasks that use DB sessions must close them promptly.  
Check worker code for uncontextmanaged sessions.

---

## Emergency relief

Scale down to 1 API replica temporarily to reduce connection count:
```bash
docker compose up -d --scale api=1
```

Then diagnose root cause before scaling back up.

---

## Escalation

If > 50% of requests are failing due to pool exhaustion for > 10 minutes:
1. Apply emergency scale-down (above).
2. Open SEV-2 incident.
3. Consult DBA about PgBouncer deployment.
