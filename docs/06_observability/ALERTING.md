# Alerting Reference — v1.0

**Last Updated:** 2026-01-01

---

## Overview

Alerts are managed via **Prometheus Alertmanager** and defined in `infra/prometheus/alerts.yml`.  
Notifications are routed to Slack (`#ops-alerts`) and PagerDuty for P1/P2 incidents.

---

## Alert severity levels

| Severity | Response SLO | Examples |
|----------|-------------|---------|
| `critical` (P1) | 15 min | Service down, DB unreachable |
| `warning` (P2) | 1 hour | High error rate, elevated latency |
| `info` | Next business day | Budget approaching limit, disk 80% |

---

## Active alert rules

### System availability

| Alert | Condition | Severity |
|-------|-----------|----------|
| `EmbedlyzerAPIDown` | `up{job="embedlyzer"} == 0` for 2 min | critical |
| `EmbedlyzerWorkerDown` | Celery heartbeat missing for 5 min | critical |
| `EmbedlyzerReadinessFailing` | `/ready` 5xx rate > 0 for 3 min | warning |

### Latency

| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighQueryLatencyP95` | p95 query latency > 8 s over 10 min | warning |
| `HighQueryLatencyP99` | p99 query latency > 15 s over 10 min | critical |
| `HighEmbeddingLatency` | embedding call p95 > 2 s over 5 min | warning |

### Error rates

| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighAPIErrorRate` | 5xx rate > 5% of requests over 5 min | critical |
| `HighAuthFailureRate` | 401/403 rate > 20% of requests over 5 min | warning |

### Resources

| Alert | Condition | Severity |
|-------|-----------|----------|
| `DiskSpaceWarning` | Disk usage > 80% | warning |
| `DiskSpaceCritical` | Disk usage > 95% | critical |
| `MemoryPressure` | RSS > 80% of container limit for 10 min | warning |
| `DBConnectionPoolExhausted` | Pool wait time > 500 ms for 5 min | critical |

### Business / cost

| Alert | Condition | Severity |
|-------|-----------|----------|
| `TokenBudget80Percent` | Monthly tokens used > 80% of budget | info |
| `TokenBudget95Percent` | Monthly tokens used > 95% of budget | warning |
| `TokenBudgetExhausted` | `is_exhausted == 1` | critical |

---

## Runbook links

| Alert | Runbook |
|-------|---------|
| `HighQueryLatencyP95` / `P99` | [HIGH_LATENCY.md](../07_runbooks/HIGH_LATENCY.md) |
| `HighAPIErrorRate` | [HIGH_ERROR_RATE.md](../07_runbooks/HIGH_ERROR_RATE.md) |
| `EmbedlyzerWorkerDown` | [CELERY_WORKER_DOWN.md](../07_runbooks/CELERY_WORKER_DOWN.md) |
| `DBConnectionPoolExhausted` | [DB_CONNECTION_POOL.md](../07_runbooks/DB_CONNECTION_POOL.md) |
| `DiskSpaceCritical` | [DISK_FULL.md](../07_runbooks/DISK_FULL.md) |
| `MemoryPressure` | [MEMORY_PRESSURE.md](../07_runbooks/MEMORY_PRESSURE.md) |
| Index alerts | [INDEX_MISMATCH.md](../07_runbooks/INDEX_MISMATCH.md) |

---

## Silencing alerts

To silence a non-actionable alert during a maintenance window:
```bash
amtool silence add --alertname=EmbedlyzerAPIDown \
  --comment="Planned maintenance 22:00-23:00 UTC" \
  --duration=1h
```
