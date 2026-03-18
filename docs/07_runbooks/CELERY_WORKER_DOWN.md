# Runbook: Celery Worker Down

**Alert:** `EmbedlyzerWorkerDown`  
**Severity:** critical  
**Last Updated:** 2026-01-01

---

## Symptoms

- Celery heartbeat missing for > 5 minutes.
- Ingest jobs queue but never start processing.
- `GET /api/v1/ingest/runs` shows runs stuck in `queued` state.

---

## Immediate triage

```bash
# Check worker container status
docker ps -a | grep worker

# Check worker logs
docker logs embedlyzer-worker --since=10m | tail -50

# Inspect active tasks
celery -A app.workers.celery_app inspect active
```

---

## Common causes and fixes

### 1. Worker container crashed

```bash
docker compose ps worker
docker compose up -d worker
```

If the worker keeps crashing:
```bash
docker logs embedlyzer-worker --since=30m | grep -E 'Error|Traceback|Signal'
```
- Look for OOM kills: `dmesg | grep -i 'killed process'`
- If memory is the cause, see [MEMORY_PRESSURE.md](MEMORY_PRESSURE.md).

### 2. Redis broker unreachable

```bash
redis-cli -u $REDIS_URL ping
```

The worker uses Redis as its Celery broker. If Redis is down:
```bash
docker compose up -d redis
docker compose restart worker
```

### 3. Task routing misconfiguration

```bash
celery -A app.workers.celery_app inspect registered
```
Ensure the `ingest` task is registered. If not, check `app/workers/__init__.py` and `celery_app.py` imports.

### 4. Worker stuck on a hanging task

```bash
# List active tasks
celery -A app.workers.celery_app inspect active

# Revoke the stuck task (replace <task_id>)
celery -A app.workers.celery_app control revoke <task_id> --terminate
```

### 5. Environment variable missing

```bash
docker compose exec worker env | grep -E 'OPENAI|PINECONE|DATABASE|REDIS'
```
Restart after fixing:
```bash
docker compose up -d --force-recreate worker
```

---

## Clearing the queue

If the queue is poisoned with bad tasks:
```bash
celery -A app.workers.celery_app purge
```
> ⚠ This discards all queued but unprocessed tasks. Ingest runs in `queued` state must be retriggered manually.

---

## Escalation

If worker remains down for > 15 minutes and restart does not help:
1. Open SEV-2 incident.
2. Identify which ingest runs were affected and notify team.
3. If worker OOM, request infrastructure capacity increase.
