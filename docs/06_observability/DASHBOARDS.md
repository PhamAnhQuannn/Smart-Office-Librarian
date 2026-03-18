# Grafana Dashboards — v1.0

**Last Updated:** 2026-01-01

---

## Overview

Dashboard JSON files are stored in `infra/grafana/dashboards/` and provisioned automatically on container start.

Grafana is available at: `http://localhost:3001` (dev) or `https://metrics.your-domain.com` (production).

---

## Dashboard inventory

| Dashboard | UID | Description |
|-----------|-----|-------------|
| **Embedlyzer Overview** | `embedlyzer-overview` | High-level health, request rate, error rate, p95 latency |
| **Query Performance** | `embedlyzer-query` | Per-query latency, TTFT, token usage, confidence distribution |
| **Ingestion Runs** | `embedlyzer-ingest` | Run success/failure rate, chunk throughput, queue depth |
| **Infrastructure** | `embedlyzer-infra` | CPU, memory, disk, DB pool, Redis memory |
| **Cost / Budget** | `embedlyzer-cost` | Monthly token consumption, budget burn rate, refusal rate |

---

## Key panels — Embedlyzer Overview

| Panel | Metric | Suggested threshold |
|-------|--------|-------------------|
| API Request Rate | `rate(http_requests_total[5m])` | — |
| Error Rate (5xx) | `rate(http_requests_total{status=~"5.."}[5m])` | > 5% → alert |
| p95 Query Latency | `histogram_quantile(0.95, rate(query_latency_seconds_bucket[10m]))` | > 8 s → alert |
| Active Stream Slots | `embedlyzer_active_stream_slots` | > 80% of limit |
| DB Pool Wait | `embedlyzer_db_pool_wait_ms_p95` | > 500 ms → alert |

---

## Key panels — Query Performance

| Panel | Description |
|-------|-------------|
| TTFT (time-to-first-token) | Latency between request receipt and first SSE delta |
| Answer vs. Refusal rate | Proportion of queries answered vs. refused (below threshold) |
| Confidence distribution | Histogram of HIGH / MEDIUM / LOW confidence results |
| Prompt + completion tokens | Token usage per query, filtered by namespace |

---

## Importing dashboards manually

1. Open Grafana → **Dashboards** → **Import**.
2. Upload the JSON from `infra/grafana/dashboards/<dashboard-name>.json`.
3. Set the Prometheus data source when prompted.

---

## Adding a new panel

1. Open the target dashboard → **Edit**.
2. Click **Add panel** → configure the PromQL query.
3. Export the updated JSON and commit it to `infra/grafana/dashboards/`.

```bash
# Export via Grafana API
curl -s http://admin:admin@localhost:3001/api/dashboards/uid/embedlyzer-overview \
  | jq '.dashboard' > infra/grafana/dashboards/embedlyzer-overview.json
```
