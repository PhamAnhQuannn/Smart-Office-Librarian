# Runbook: Memory Pressure

**Alert:** `MemoryPressure`  
**Severity:** warning (RSS > 80% of container limit for 10 min)  
**Last Updated:** 2026-01-01

---

## Symptoms

- `container_memory_usage_bytes` / `container_spec_memory_limit_bytes` > 0.80.
- Container OOM-killed: `docker events --filter 'event=oom'`
- API/worker slow or unresponsive.

---

## Immediate triage

```bash
# Check container memory usage
docker stats --no-stream

# Check for recent OOM kills
dmesg | grep -i 'oom\|killed process' | tail -20

# Check Python memory inside the container
docker exec embedlyzer-api python -c "
import tracemalloc, time
tracemalloc.start()
"
```

---

## Common causes and fixes

### 1. Embedding model loaded in process

If using a local embedding model (not OpenAI), it may be consuming large RSS.
- Move to OpenAI API or a dedicated embedding service.
- Or increase container memory limit.

### 2. Large SSE buffers not being released

```bash
# Check active stream count
curl -s http://localhost:8000/metrics | grep embedlyzer_active_stream_slots
```

If many streams are open:
- Check `STREAM_SLOT_TTL` (default 90 s) — orphaned slots should be cleaned up.
- Restart the API if slots are stuck: `docker compose restart api`

### 3. Redis memory (if using Redis for caching)

```bash
redis-cli -u $REDIS_URL info memory | grep used_memory_human
redis-cli -u $REDIS_URL info keyspace
```

Set a `maxmemory` policy:
```
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 4. PostgreSQL shared_buffers too high

```sql
SHOW shared_buffers;
```

Reduce in `postgresql.conf` and restart Postgres if it's taking too much host memory.

### 5. Worker holding large ingestion payloads

Celery workers that chunk large files hold the entire file in memory.
- Reduce `BATCH_SIZE` for ingest tasks.
- Increase worker container memory limit.

---

## Emergency — OOM imminent

If RSS > 95% and container is about to be killed:
```bash
# Gracefully restart API (serves in-flight requests first)
docker compose restart api

# If worker is the culprit
docker compose restart worker
```

---

## Long-term prevention

1. Set container memory limits in `docker-compose.yml`:
   ```yaml
   mem_limit: 1g
   memswap_limit: 1g
   ```
2. Enable Prometheus memory alerts at 70% for early warning.
3. Profile with `memory-profiler` or `memray` in staging if leak is suspected.

---

## Escalation

If container keeps OOM-killing after restart:
1. Open SEV-2 incident.
2. Immediately scale down to reduce load.
3. Enable debug memory profiling in staging and reproduce.
