# Runbook: High Query Latency

**Alert:** `HighQueryLatencyP95` / `HighQueryLatencyP99`  
**Severity:** warning (P95 > 8 s) / critical (P99 > 15 s)  
**Last Updated:** 2026-01-01

---

## Symptoms

- `query_latency_seconds` p95 exceeds 8 s sustained over 10 minutes.
- Users report slow or timing-out query responses.
- TTFT (time-to-first-token) metrics elevated.

---

## Immediate triage

```bash
# Check application logs for slow queries
docker logs embedlyzer-api --since=10m | grep '"latency_ms"' | sort -t: -k2 -rn | head -20

# Check upstream OpenAI latency
curl https://status.openai.com/api/v2/status.json | jq '.status'

# Check Pinecone latency
docker logs embedlyzer-api --since=10m | grep 'pinecone'
```

---

## Common causes and fixes

### 1. OpenAI API degraded
- Check [https://status.openai.com](https://status.openai.com).
- If degraded, latency is external — inform users and wait for recovery.
- Consider enabling `RETRIEVAL_ONLY` fallback mode.

### 2. Pinecone index hot / cold start
```bash
# Query Pinecone index stats
curl -s https://controller.<env>.pinecone.io/databases | jq '.'
```
- Warm index by issuing a test query.
- Check index region matches API deployment region.

### 3. Large prompt (many source citations)
- Check `MAX_SNIPPET_CHARS` setting (default 500).
- Reduce `top_k` retrieval count in config.

### 4. Database slow query (logging lookup)
```sql
SELECT query, calls, mean_exec_time FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```
- Add missing indexes if query log writes are slow.
- Check DB connection pool saturation (see [DB_CONNECTION_POOL.md](DB_CONNECTION_POOL.md)).

### 5. Under-provisioned API pod
```bash
# Check CPU/memory usage
docker stats embedlyzer-api
```
- Scale up replica count or increase CPU/memory limits.

---

## Escalation

If latency remains > 15 s p99 for > 15 minutes with no upstream degradation:
1. Page the on-call engineer via PagerDuty.
2. Open a SEV-2 incident in the incident log.
3. Consider routing traffic to a backup region if configured.
