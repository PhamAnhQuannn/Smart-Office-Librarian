# Observability Documentation

**Version:** v1.3  
**Status:** Production Observability Guidelines  
**Last Updated:** 2026-03-11  
**Compliance:** REQUIREMENTS.md NFR-1.x (Performance), NFR-3.1 (Availability), NFR-6.x (Observability), OPERATIONS.md Section 2  

> This document defines metrics, logging, tracing, SLO targets, and alerting strategies for the Smart Office Librarian RAG system to enable proactive monitoring, rapid troubleshooting, and continuous performance optimization.  
>
> **Canonical changes in v1.3:** clarified availability SLO exclusion rules (429 + retrieval-only mode), extended latency histogram buckets for degradation scenarios, clarified worker heartbeat TTL assumptions, required auto-expiry for dynamic trace sampling escalation, strengthened Prometheus label hygiene rules, and hardened exporter attribute filtering requirements.

---

## Overview

Observability ensures that the system's internal state can be inferred from external outputs (metrics, logs, traces). This enables:

* **Proactive Detection:** Identify issues before users are impacted
* **Rapid Troubleshooting:** Reduce MTTR (Mean Time To Resolution) with structured diagnostics
* **Performance Optimization:** Data-driven decisions on tuning and scaling
* **SLO Compliance:** Track and enforce Service Level Objectives
* **Cost Management:** Monitor token consumption and budget adherence

**Three Pillars of Observability:**

1. **Metrics:** Quantitative measurements (counters, gauges, histograms)
2. **Logs:** Discrete event records with context and severity
3. **Traces:** Distributed request flow tracking across services

**Privacy & Cardinality Principles (applies across the doc):**

* Do **not** emit high-cardinality identifiers (raw user IDs, email addresses) as Prometheus metric labels. Use low-cardinality labels only (`namespace`, `role`, `tenant_id`) and `user_bucket` (coarse bucketing) for very coarse grouping when necessary (see Metric Cardinality Best Practices, Section 1.5).
* `user_pseudonym` (sha256(sub) truncated) is allowed in structured logs and traces only — **never** as a Prometheus label.
* If you require per-user analysis for business intelligence, stream events to an analytics pipeline (Kafka → ClickHouse / BigQuery).

---

## 1. Metrics (Prometheus)

### 1.1 Metrics Endpoint (Canonical)

**Endpoint:** `GET /metrics` (per ARCHITECTURE.md Invariant G)

* Prometheus-compatible exposition format.
* **Network access restriction required:** `/metrics` MUST NOT be publicly routable. It must be accessible only to authorized Prometheus server(s) via private network, VPC, VPN, or cluster-internal service accounts. If running on Kubernetes, use NetworkPolicies and RBAC to restrict access.
* Optional proxy route: `GET /api/v1/metrics` only when the proxy enforces strong network restrictions and relabeling to remove or replace any sensitive labels.
* Scrape interval: 15 seconds (configurable).

> **Note:** Do not rely on HTTP auth alone for `/metrics`. Use network-level controls, firewall rules, and Prometheus scrape ACLs.

### 1.2 Core Metrics Categories

> **Labeling rule:** Avoid high-cardinality labels. **Do not** use raw `user_id`, email, or `user_pseudonym` as Prometheus labels. Allowed low-cardinality labels include `namespace`, `role` (admin/user), `tenant_id` (only if low-cardinality), `model_id`, `operation`, and `user_bucket` (see Section 1.5 — coarse bucketing only). For per-user analytics use an event/analytics pipeline — not Prometheus.

#### Query Pipeline Metrics

**Throughput:**

* `query_requests_total` (counter) — Total query requests received. Labels: `namespace`, `status` (success/refusal/error), `role` (admin/user), `user_bucket` (optional; see Section 1.5).
* `query_requests_per_second` (gauge) — Current request rate (QPS). Labels: `namespace`.
* `concurrent_queries` (gauge) — Number of queries in-flight. Labels: `namespace`.

**Latency (Histograms with p50/p95/p99):**

* `query_latency_seconds` — End-to-end query latency (user request → response complete). Labels: `namespace`, `refusal_status` (generated/refused), `error_code`.

  * Buckets: `[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]`
* `retrieval_latency_seconds` — Vector search + reranking time. Labels: `namespace`.

  * SLO target: p95 ≤ 500ms (NFR-1.2).
* `generation_latency_seconds` — LLM generation time (excluding retrieval). Labels: `model_id`.
* `ttft_seconds` — Time-to-First-Token (streaming responsiveness). Labels: `model_id`.

  * SLO target: p95 ≤ 500ms (NFR-1.3).

**Outcome Metrics:**

* `query_refusal_total` (counter) — Queries refused due to low similarity scores. Labels: `namespace`, `threshold_bucket`.
* `query_retrieval_only_total` (counter) — Queries served in retrieval-only mode (budget cap or LLM unavailable). Labels: `namespace`, `reason` (budget/llm_unavailable).
* `query_errors_total` (counter) — Query errors by error code. Labels: `error_code`, `error_type` (client_error/server_error/dependency_error).

**Cost Metrics:**

* `embedding_tokens_total` (counter) — Total embedding tokens consumed. Labels: `model_id`, `cache_hit` (true/false), `namespace`.
* `llm_tokens_total` (counter) — Total LLM tokens consumed (prompt + completion). Labels: `model_id`, `operation` (generation/fallback), `namespace`.
* `budget_utilization_ratio` (gauge) — Current spend as fraction of budget cap (0.0-1.0). Labels: `namespace`.

  * Alert threshold: ≥ 0.80.

#### Ingestion Pipeline Metrics

**Job Metrics:**

* `ingestion_jobs_total` (counter) — Ingestion jobs started. Labels: `source_type` (github/confluence), `status` (success/failure), `namespace`.
* `ingestion_duration_seconds` (histogram) — Time to complete ingestion job. Labels: `source_type`.
* `ingestion_chunks_created_total` (counter) — Total chunks indexed. Labels: `source_type`, `namespace`.
* `ingestion_failures_total` (counter) — Failed ingestion jobs. Labels: `source_id`, `failure_reason`.

**Worker Health:**

* `worker_heartbeat_age_seconds` (gauge) — Time since last worker heartbeat (per worker ID).
  * **TTL assumption:** worker heartbeat interval/TTL = 60 seconds.
  * **Alert threshold:** > 180 seconds (3x TTL).
* `worker_queue_depth` (gauge) — Number of pending ingestion tasks in Celery queue. Labels: `queue_name`.

#### Dependency Health Metrics

**External Services:**

* `dependency_health` (gauge) — Health status of external dependencies (1=healthy, 0=unhealthy). Labels: `service` (postgresql/redis/pinecone/openai).
* `dependency_request_duration_seconds` (histogram) — Latency of external API calls. Labels: `service`, `operation`.
* `dependency_errors_total` (counter) — Failed external API calls. Labels: `service`, `error_type`.

**Cache Performance:**

* `cache_hit_ratio` (gauge) — Embedding cache hit ratio (rolling 5-minute window). Target: ≥ 0.30.
* `cache_evictions_total` (counter) — Redis cache evictions by key pattern.
* `retrieval_cache_hit_total` (counter) — Retrieval cache hits (if enabled per DECISIONS.md 8.2).

#### RBAC & Security Metrics

**Access Control (low-cardinality only):**

* `rbac_denials_total` (counter) — Queries denied due to RBAC filter (no matching chunks with user permissions). Labels: `namespace`, `role`, `denial_reason`.
* `rate_limit_exceeded_total` (counter) — Rate limit rejections (HTTP 429). Labels: `namespace`, `role`.
* `break_glass_access_total` (counter) — Break-glass raw query text access events. Labels: `requester_role`, `approver_role`.

**Audit Events:**

* `admin_actions_total` (counter) — Admin actions performed. Labels: `action_type` (threshold_update/source_create/source_delete/swap_index), `admin_role`.

### 1.3 Resource Metrics (System-Level)

**Compute:**

* `cpu_usage_percent` (gauge) — CPU utilization. Alert threshold: > 80% sustained (load-shedding trigger per NFR-1.5).
* `memory_usage_bytes` (gauge) — Memory consumption.
* `disk_usage_bytes` (gauge) — Disk usage by mount point.

**Network:**

* `http_requests_total` (counter) — Total HTTP requests by endpoint and status code. Labels: `endpoint`, `status_code`.
* `http_request_size_bytes` (histogram) — Request body sizes.
* `http_response_size_bytes` (histogram) — Response body sizes.

### 1.4 Alerting-related Metric Guidelines

* Use **recording rules** for expensive or frequently computed aggregates (p95/p99) to keep alert queries fast.
* Avoid complex joins in alert rules; rely on precomputed recording rules.
* Use `namespace` to scope alerts to staging/production/dev appropriately.
* Add `prometheus_ingest_cardinality_estimate` metric and alert on unexpected growth (see Appendix A checklist).

### 1.5 Metric Cardinality Best Practices

1. **Never emit raw identifiers** (emails, user IDs) as Prometheus labels.
2. **Do not** emit `user_pseudonym` as a Prometheus label. `user_pseudonym` is allowed only in logs & traces (treated as PII).
3. If coarse per-user grouping is required in Prometheus, only use `user_bucket` computed as `sha256(sub) % 100` (stable 100-bucket distribution). Keep bucket modulus small (≤ 100).
4. Limit label combinations — each unique label-value combination creates a new time series. Keep label space small (`namespace`, `role`, `model_id`).
5. Use recording rules to precompute p95/p99 and other costly aggregates.
6. For per-user analytics, stream events to an analytics system (Kafka → ClickHouse / BigQuery), not Prometheus.
7. Monitor cardinality: add and alert on `prometheus_ingest_cardinality_estimate` to detect regressions early.

**Client-side `user_bucket` example (recommended):**

```python
import hashlib

def user_bucket(sub: str, modulus: int = 100) -> str:
    h = hashlib.sha256(sub.encode('utf-8')).hexdigest()
    return str(int(h, 16) % modulus)
# Emit metric label user_bucket=user_bucket(sub) only (do NOT emit user_pseudonym)
````

**Enforcement:** Instrumentation guidelines must be followed by all services. CI enforcement lives in the separate CI/CD document.

---

## 2. Logs (Structured JSON)

### 2.1 Logging Standards (Canonical)

**Format:** Structured JSON.

**Required Fields (Every Log Entry):**

* `timestamp` (ISO 8601 UTC)
* `level` (DEBUG/INFO/WARNING/ERROR/CRITICAL)
* `service` (api/worker/ingestion)
* `environment` (dev/staging/production)
* `trace_id` (OpenTelemetry trace ID for correlation)
* `span_id` (OpenTelemetry span ID)
* `message` (human-readable summary)

**Contextual Fields (When Applicable):**

* `user_pseudonym` (sha256(sub)[:12] — PII flagged, pseudonymized) — **logs & traces only**
* `user_bucket` (optional; low-cardinality coarse bucket)
* `query_id` (UUID for query tracking)
* `namespace`
* `error_code` (from error catalog)
* `latency_ms` (operation duration)

> **PII note:** `user_pseudonym` is a pseudonymized identifier and must be treated as PII in downstream analytics. Do not expose `user_pseudonym` to external vendors without a DPA and masking.

### 2.2 Redaction Rules (MANDATORY)

**NEVER log:**

* Raw `Authorization` headers or Bearer tokens
* Full API keys (log first 4 characters only: `sk-ab**`)
* Raw query text (log `query_hash` instead; see DATA_GOVERNANCE.md)
* User email addresses (log `user_pseudonym` only)
* Stream tokens or query string tokens
* Raw file content or source document text
* JWT payloads (log `sub` only as `user_pseudonym`, and `role`)
* PII patterns (emails, phone numbers, SSNs)

**MUST log (with redaction):**

* Query hashes (SHA-256)
* Error messages (sanitize stack traces to remove secrets)
* Stage latency breakdowns (retrieval_ms, generation_ms)
* Refusal reasons (threshold, top score, confidence level)
* Job IDs and source identifiers
* Admin actions with audit context (who, when, what scope) — record `user_pseudonym` and `admin_role`.

### 2.3 Log Levels & Usage

**DEBUG:** Verbose diagnostics (disabled in production by default) — cache hits/misses, internal retries, detailed stage timing (redacted).
**INFO:** Normal operational events — query started/completed, ingestion job started/completed, threshold updated.
**WARNING:** Degraded performance or unusual conditions — retrieval-only mode activated, slow upstream dependency.
**ERROR:** Operation failures requiring attention — query failed, ingestion job failed, dependency unavailable.
**CRITICAL:** System-level failures impacting availability — DB connection lost, Redis unavailable, disk critically low.

### 2.4 Redaction & Aggregation Implementation Examples

**Fluent Bit (example) — redaction via Lua filter**: implement a small Lua script `redact.lua` to replace PII patterns before forwarding logs.

`fluent-bit.conf` (snippet):

```ini
[FILTER]
    Name    lua
    Match   *
    script  /fluent-bit/scripts/redact.lua
    call    redact
```

`redact.lua` (example pseudocode, put in ops repo and expand as needed):

```lua
function redact(tag, timestamp, record)
  local msg = record["message"]
  -- replace emails
  msg = msg:gsub("([%w%.%-_]+@[%w%.%-_]+%.[%a]+)","[EMAIL_REDACTED]")
  -- replace phone-like patterns (very permissive example)
  msg = msg:gsub("%+?%d[%d%-%s%(%)]%d%d%d%d%d+","[PHONE_REDACTED]")
  record["message"] = msg
  return 1, timestamp, record
end
```

**Note:** Use tested, jurisdiction-appropriate regexes; ensure your redaction script is kept up-to-date.

### 2.5 Retention & Access

* **Operational Logs:** 14 days hot, 90 days cold archive (see Operations).
* **Audit Logs:** 1 year minimum retention (per DATA_GOVERNANCE.md).
* **Access Control:** Operational logs available to authenticated operators; audit logs restricted to admins with explicit access logging.
* **Dashboards & Traces Access:** Any dashboard or tracing UI that can display `user_pseudonym` or other PII must have strict RBAC and access auditing enabled (Grafana/Jaeger roles). Document permitted roles and approval process in OPERATIONS.md.

---

## 3. Traces (OpenTelemetry)

### 3.1 Distributed Tracing Architecture

* **Instrumentation:** OpenTelemetry Python SDK.
* **Trace Propagation:** W3C Trace Context headers (`traceparent`, `tracestate`).
* **Exporter:** OTLP to backend (Jaeger, Tempo, or cloud provider).

### 3.2 Trace Spans (Query Path)

**Parent Span:** `POST /api/v1/query`

**Child Spans:**

1. `authentication.verify_jwt` — JWT validation and user extraction
2. `rbac.build_filter` — Construct RBAC metadata filter
3. `index_safety.check_version` — Verify model_id and index_version match
4. `cost.check_budget` — Budget gating decision
5. `threshold.fetch` — Retrieve threshold for namespace
6. `pipeline.run` — RAG pipeline orchestration

   * `embedder.embed_query` — Query embedding (with cache check)
   * `retrieval.search` — Pinecone vector search
   * `reranker.rerank` — Cross-encoder reranking
   * `refusal.check` — Threshold comparison
   * `generation.generate` — LLM generation (SSE streaming)
7. `query_log.write` — Persist query log to database

**Span Attributes (Required):**

* `user_pseudonym` (sha256(sub)[:12]) — pseudonymized user identifier (PII; treat carefully)
* `namespace`
* `query_id`
* `model_id`, `index_version`
* `top_k`, `top_n`, `threshold`
* `cache_hit` (embedding cache)
* `refusal_status` (generated/refused)
* `error_code` (if failed)

> **Privacy rule:** **Do not** include raw query text or document snippets in span attributes. Use `query_hash` for correlation.

### 3.3 Trace Spans (Ingestion Path)

**Parent Span:** `POST /api/v1/ingest` (admin-initiated)

**Child Spans:**

1. `connector.fetch_tree` — GitHub API list files
2. `connector.fetch_content` — Fetch file content (per file) — **do not** include file content in traces; include `file_path` only.
3. `chunker.chunk` — Tokenize and chunk file
4. `embedder.embed_batch` — Batch embedding generation
5. `vector_db.upsert` — Pinecone vector upsert
6. `postgres.insert_chunks` — Insert chunk metadata
7. `ingestion.finalize` — Atomic source metadata update

### 3.4 Sampling Strategy

**Development/Staging:** 100% sampling.
**Production:**

* Success cases: 10% sampling.
* Errors/Timeouts: 100% sampling (always trace failures).
* Slow requests (> p95 threshold): 100% sampling.

**Dynamic escalation:** On SEV-2/SEV-1 conditions or budget anomalies, temporarily increase sampling to 100% for affected `namespace` for a configured window.

* **Auto-expiry required:** escalation must automatically revert to baseline after TTL (default: 10 minutes) to avoid accidental sustained 100% sampling.
* Implement via a central sampling controller or OTEL remote sampler config.

**Override:** Admin debugging may set `X-Trace-Override: 1` to force tracing (audited).

### 3.5 Trace Retention & Export Hygiene

* **Hot storage (queryable):** 7 days.
* **Cold storage (archive):** 30 days (optional).
* **Exporter hygiene:** Configure OTLP exporter to drop sensitive attributes before export:

  * Drop attributes named `raw_query`, `document_snippet`, or any configured sensitive key list.
  * Drop any attribute matching configured regexes (defense-in-depth).
  * Validate by injecting test spans in staging and verifying exported payloads contain no forbidden keys.

---

## 4. SLO Targets (Service Level Objectives)

### 4.1 Availability SLO

* **Target:** 99.9% monthly uptime (per REQUIREMENTS NFR-3.1).
* **Exclusions:** Third-party outages (OpenAI, Pinecone), scheduled maintenance.
* **Additional availability accounting clarification:**

  * HTTP **429** responses due to deliberate rate-limits are not counted as availability failures.
  * Retrieval-only mode responses are not counted as availability failures (feature degradation is tracked separately as a SEV-3).
* **Error Budget:** 43.2 minutes downtime per month.
* **Alerting:** Alert when error budget consumption exceeds 50% within 7 days.

### 4.2 Latency SLOs

**Query End-to-End Latency:**

* **Target:** p95 ≤ 2.0 seconds (under load context: ≤ 100 concurrent users, ≤ 10 QPS).
* **Measurement Window:** Rolling 1-hour.
* **Alert Threshold:** p95 > 2.0s sustained for 3 consecutive windows (trigger load-shedding procedure per NFR-1.5).

**Retrieval Latency:** p95 ≤ 500ms (vector search + reranking). Alert if p95 > 700ms for 5 minutes.
**TTFT:** p95 ≤ 500ms for Time-to-First-Token. Alert if p95 > 750ms for 5 minutes.

### 4.3 Throughput SLO

* **Ingestion Throughput:** ≥ 200 documents/minute (subject to external API limits). Measured as `ingestion_chunks_created_total / elapsed_time`.

### 4.4 Refusal Rate Target

* **Operational Target:** < 30% refusal rate in production.
* **Alert:** Refusal rate > 40% sustained for 1 hour → SEV-2 (investigate corpus quality or threshold tuning).

### 4.5 Cost SLO

* **Warning Threshold:** ≥ 80% of monthly budget.
* **Hard Cap:** 100% (triggers retrieval-only mode).
* **Measurement:** `budget_utilization_ratio` gauge by `namespace`.
* **Mitigation:** When budget utilization reaches hard cap trigger, system transitions to retrieval-only mode; alerting must include runbook and dashboard links (see Section 5).

---

## 5. Alerting Strategy

### 5.1 Alerting Principles

1. **Actionable:** Every alert must link to a runbook and have a clear owner.
2. **Low Noise:** Tune thresholds to avoid fatigue.
3. **Severity-based routing:** SEV-1 pages on-call; SEV-2 creates tickets; SEV-3 logs for business-hours triage.
4. **Contextual:** Include relevant metrics, Grafana dashboard links, top traces, and recent logs in the alert payload.

### 5.2 Alert Payload Requirements (REQUIRED)

All alert notifications (PagerDuty/Slack/email) **must** include these fields (when available):

* `runbook_url` — URL to the canonical runbook for the alert condition.
* `dashboard_url` — URL to the dashboard panel showing the metric(s) that fired.
* `top_trace_link` — Link to top traces in tracing system filtered by alert window & namespace.
* `recent_logs_query` — Link to prefilled logs search (Loki/ELK) for the alert window.
* `affected_namespace` — `namespace` value.
* `alert_severity` — SEV-1/SEV-2/SEV-3/SEV-4.
* `summary` and `details` — brief description + suggested initial actions.

> **Implementation note:** Configure Alertmanager templates to populate these fields. See the Alertmanager template example below.

### 5.3 Alert Severity Levels (Canonical)

**SEV-1 (Critical - Page On-Call):** API completely unavailable, DB unavailable, data loss risk, security incident.
**SEV-2 (High - Immediate Investigation):** Elevated error rate (> 5%), SLO breach projected, dependency critical degradations, ingestion failure spikes, cost anomalies.
**SEV-3 (Medium - Business Hours Investigation):** Feature degradation (LLM down, retrieval-only mode), worker lag, cache problems.
**SEV-4 (Low - Informational):** Maintenance notifications, index swap success, cost warning (≥ 80%).

### 5.4 Sample Runbooks (link placeholders)

* Database Unavailable (SEV-1): `runbook_url`: `https://ops.example.com/runbooks/db-unavailable`
* API Latency SLO Breach (SEV-2): `runbook_url`: `https://ops.example.com/runbooks/latency-slo-breach`
* Budget Exceeded (SEV-2): `runbook_url`: `https://ops.example.com/runbooks/budget-exceeded`

(Ensure these runbook URLs exist in OPERATIONS.md and are kept up-to-date.)

### 5.5 Critical Alerts & Runbooks (Examples)

#### Database Unavailable (SEV-1)

**Condition:** PostgreSQL health check failing for > 1 minute.
**Alert payload fields:** `runbook_url`, `dashboard_url`, `top_trace_link`, `recent_logs_query`.
**Runbook summary:** Check DB connectivity, failover to replica, restore from replica, contact DBA. See `runbook_url`.

#### API Latency SLO Breach (SEV-2)

**Condition:** `job:query_latency_seconds_p95{namespace="production"} > 2.0` for 3 consecutive 1-minute windows.
**Runbook summary:** Check dependencies, CPU/memory, slow traces, and consider horizontal scaling. See `runbook_url`.

#### Budget Exceeded (SEV-2)

**Condition:** `budget_utilization_ratio >= 1.0`.
**Runbook summary:** Verify retrieval-only mode, analyze query logs for abuse, contact finance. See `runbook_url`.

### 5.6 Alertmanager Template Guidance (example annotations)

Configure Alertmanager to include runbook/dashboard links in the notification payloads. Example annotation template fields (adjust per platform):

```yaml
annotations:
  runbook_url: "https://ops.example.com/runbooks/{{ .GroupLabels.alertname }}"
  dashboard_url: "https://grafana.example.com/d/{{ .GroupLabels.dashboard_id }}?var-namespace={{ .Labels.namespace }}"
  top_trace_link: "https://traces.example.com/search?namespace={{ .Labels.namespace }}&from={{ .StartsAt }}&to={{ .EndsAt }}"
  recent_logs_query: "https://logs.example.com/search?query=namespace:{{ .Labels.namespace }}+alertname:{{ .GroupLabels.alertname }}&from={{ .StartsAt }}&to={{ .EndsAt }}"
```

(Implement concrete templating per your Alertmanager / notification integration.)

---

## 6. Dashboards

### 6.1 Operational Dashboard (Primary)

**Panels:**

1. Traffic Overview — QPS, concurrent queries, status breakdown.
2. Latency Heatmaps — p50/p95/p99 end-to-end, retrieval, generation, TTFT.
3. Error Rates — errors by `error_code` and dependency errors.
4. Cost Tracking — budget utilization, LLM/embedding tokens consumed, 7-day projection.
5. Dependency Health — Postgres, Redis, Pinecone, OpenAI health and latency.

**Access controls:** Dashboards that can display `user_pseudonym` or PII must have RBAC enabled and access logged. Only roles with documented justification may view pseudonymized traces/logs.

### 6.2 Ingestion Dashboard

**Panels:**

1. Worker queue depth.
2. Ingestion job success/failure rates.
3. Chunks created per minute.
4. Job duration histogram.
5. Worker heartbeat staleness.

### 6.3 User Experience Dashboard

**Panels:**

1. Refusal rate trend (by `namespace`).
2. Retrieval-only mode activations.
3. Rate limit rejections (by `namespace`, `role`).
4. Query latency percentiles by `namespace`.
5. Top user-facing error codes.

### 6.4 SLO Compliance Dashboard

**Panels:**

1. Availability % (rolling 30 days).
2. Error budget remaining.
3. Latency SLO compliance (% queries < 2.0s).
4. TTFT SLO compliance (% queries < 500ms).

---

## 7. Operational Procedures

### 7.1 Metric Collection

**Prometheus Configuration (example):**

```yaml
scrape_configs:
  - job_name: 'smart-office-librarian-api'
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets: ['api:8000']
    relabel_configs:
      # Drop forbidden labels if present (defense-in-depth).
      # NOTE: This does not prevent emission; instrumentation MUST NOT emit these labels.
      - action: labeldrop
        regex: user_id
      - action: labeldrop
        regex: user_pseudonym
```

**Recommended client-side change:** Stop passing `user_id` or `user_pseudonym` into Prometheus client metrics; replace with `user_bucket` if very coarse grouping is required (client-side computed).

### 7.2 Prometheus Recording Rules & Sample Alert Rules

**Recording rules (example):**

```yaml
groups:
- name: smart-office-recording
  rules:
  - record: job:query_latency_seconds_p95
    expr: histogram_quantile(0.95, sum(rate(query_latency_seconds_bucket[5m])) by (le, namespace))
  - record: job:query_latency_seconds_p99
    expr: histogram_quantile(0.99, sum(rate(query_latency_seconds_bucket[5m])) by (le, namespace))
```

**Alert rule (example p95 breach → SEV-2):**

```yaml
groups:
- name: smart-office-alerts
  rules:
  - alert: QueryLatencyP95Breach
    expr: job:query_latency_seconds_p95{namespace="production"} > 2.0
    for: 3m
    labels:
      severity: SEV-2
    annotations:
      summary: "p95 query latency > 2.0s (prod)"
      runbook_url: "https://ops.example.com/runbooks/latency-slo-breach"
```

### 7.3 Prometheus Relabeling & Hash-bucketing

If you need very coarse per-user grouping in Prometheus, compute `user_bucket` client-side as `sha256(sub) % 100` and emit only `user_bucket`.

> **Do not** rely on Prometheus relabeling to compute `user_bucket` from `user_pseudonym` in production. `user_pseudonym` must not be emitted as a label, and server-side hashing increases scrape-time CPU. Prefer client-side bucketing.

### 7.4 Log Aggregation & Redaction

**Log Shipping:** Fluent Bit / Fluentd → Loki / Elasticsearch / CloudWatch.
**Retention:** Operational logs 14 days hot + 90 days cold archive; Audit logs 1 year minimum.
**Redaction:** Implement a redaction filter (Lua example shown in Section 2.4) to strip emails/phone/SSNs before forwarding.
**Access:** Audit logs restricted to admins with additional access logging.

### 7.5 Trace Sampling Configuration (env vars)

```bash
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling in production
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318
```

Dynamic sampling escalation must have auto-expiry (see 3.4).

### 7.6 Health Checks

**Liveness Probe:** `GET /health` — returns 200 if service process running (no dep checks).
**Readiness Probe:** `GET /ready` — returns 200 only if service and dependencies are healthy (Postgres, Redis, Pinecone).
**Startup Probe:** `GET /health` with longer timeout.

### 7.7 Network Protection Example (Kubernetes NetworkPolicy)

Protect `/metrics` from public access. Example NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: smart-office
spec:
  podSelector:
    matchLabels:
      app: smart-office-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9100
```

(Adapt port/labels to your cluster/service.)

---

## 8. Related Documents

* [Requirements](../../Backbond/REQUIREMENTS.md) — NFR-1.x (Performance), NFR-3.1 (Availability), NFR-6.x (Observability)
* [Operations](../../Backbond/OPERATIONS.md) — Monitoring, alerting configuration, incident response
* [Architecture](../../Backbond/ARCHITECTURE.md) — Invariant G (metrics endpoint), telemetry integration
* [Decisions](../../Backbond/DECISIONS.md) — Caching policies (TTLs), rate limits
* [Data Governance](../08_governance/DATA_GOVERNANCE.md) — Logging redaction rules, retention policies
* [Security](../04_security/SECURITY.md) — Audit logging, break-glass access tracking

---

## 9. Version History

| Version | Date       | Changes                                                                                                                                                                                                                                                                                                                                         |
| ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0    | 2026-03-11 | Initial observability documentation.                                                                                                                                                                                                                                                                                                            |
| v1.1    | 2026-03-11 | Cardinality & privacy fixes: removed raw `user_id` from Prometheus labels; introduced `user_pseudonym`/`user_bucket` guidance; added `/metrics` network-access controls and Prometheus relabel examples; required runbook links and alert payload fields; added metric-cardinality best practices and dynamic sampling guidance.                |
| v1.2    | 2026-03-11 | Corrected Prometheus relabel examples; prohibited `user_pseudonym` as a Prometheus label (logs/traces only); added concrete recording rules and sample alert rule; added NetworkPolicy example to harden `/metrics`; added Fluent Bit redaction example; added OTLP exporter attribute filtering guidance; tightened dashboard access controls. |
| v1.3    | 2026-03-11 | Clarified availability SLO accounting (429 + retrieval-only mode); extended histogram buckets for severe degradation; clarified worker heartbeat TTL assumption; required dynamic sampling escalation auto-expiry; strengthened label hygiene language; hardened OTLP exporter attribute filtering validation guidance.                         |

---

## Appendix A — Quick Implementation Checklist (priority order)

1. [ ] Remove `user_id` and `user_pseudonym` labels from Prometheus client instrumentation. Replace with `namespace`, `role`, `tenant_id`, or `user_bucket`.
2. [ ] Harden `/metrics` network access (firewall/NW ACLs/serviceAccount). Document scrape ACLs (use Kubernetes NetworkPolicy example).
3. [ ] Update loggers to emit `user_pseudonym` (sha256(sub)[:12]) in logs & traces and ensure pseudonymization is applied consistently — **never** emit `user_pseudonym` as a Prometheus label.
4. [ ] Implement Prometheus recording rules for p95/p99 and budget_utilization_ratio (examples included).
5. [ ] Add `runbook_url`, `dashboard_url`, `top_trace_link`, and `recent_logs_query` into Alertmanager templates and verify runbook pages exist.
6. [ ] Ensure OTLP exporter attribute filters drop any `raw_query` / `document_snippet` attributes before export; validate with test spans in staging.
7. [ ] Implement dynamic trace-sampling escalation for incidents with **auto-expiry TTL** (default 10 minutes).
8. [ ] Add `prometheus_ingest_cardinality_estimate` metric and alert if it grows unexpectedly.
9. [ ] Add Fluent Bit redaction filters and test with PII injection scenarios.
10. [ ] Simulate high-cardinality emit in staging to validate Prometheus stability.
11. [ ] Document all changes in RELEASE_NOTES and notify on-call & security teams.
12. [ ] CI enforcement lives in the separate CI/CD document (scan for forbidden metric labels and fail PRs that add them).

