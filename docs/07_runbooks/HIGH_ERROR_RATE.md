# Runbook: High API Error Rate

**Alert:** `HighAPIErrorRate`  
**Severity:** critical (5xx rate > 5% over 5 min)  
**Last Updated:** 2026-01-01

---

## Symptoms

- `http_requests_total{status=~"5.."}` exceeds 5% of total requests.
- Users receive unexpected 500/502/503 responses.
- Error rate dashboard panel in red.

---

## Immediate triage

```bash
# Tail error logs
docker logs embedlyzer-api --since=5m | grep '"level":"error"'

# Identify which endpoint is failing
docker logs embedlyzer-api --since=5m | grep '"status":5' | jq '.path' | sort | uniq -c | sort -rn
```

---

## Common causes and fixes

### 1. Database connection failure
```bash
# Check Postgres is up
docker ps | grep postgres
docker logs embedlyzer-postgres --since=5m | tail -30
```
- If Postgres is down, restart it and verify `DATABASE_URL` is correct.
- See [DB_CONNECTION_POOL.md](DB_CONNECTION_POOL.md) if pool is exhausted.

### 2. OpenAI API errors (502 upstream)
```bash
docker logs embedlyzer-api --since=5m | grep 'openai'
```
- Check [https://status.openai.com](https://status.openai.com).
- Rate limit hit: check `X-RateLimit-Remaining-Requests` in logs and reduce concurrency.

### 3. Pinecone 5xx
```bash
docker logs embedlyzer-api --since=5m | grep 'pinecone'
```
- Check Pinecone status page.
- Verify `PINECONE_API_KEY` and index name are correct.

### 4. Unhandled exception in new deployment
```bash
# Check recent deployment
git log --oneline -5
docker logs embedlyzer-api --since=30m | grep 'Traceback\|Exception'
```
- Roll back if a recent deploy introduced the error:
  ```bash
  docker compose up -d --scale api=0 && docker compose up -d
  ```

### 5. Redis unavailable (session store / rate limiter)
```bash
docker logs embedlyzer-redis --since=5m
redis-cli -u $REDIS_URL ping
```

---

## Escalation

If 5xx rate stays above 10% for > 10 minutes:
1. Declare SEV-1 or SEV-2 incident.
2. Notify stakeholders via `#incidents` Slack channel.
3. Begin rollback procedure: [ROLLBACK_PROCEDURES.md](../../docs/09_release/ROLLBACK_PROCEDURES.md).
