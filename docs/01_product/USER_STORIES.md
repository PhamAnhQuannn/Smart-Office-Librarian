# User Stories

## Query User Stories

### US-1 Ask a question with citations
As a user, I want to ask a question and receive an answer with source citations so I can verify the response.

Acceptance criteria:
- Response streams over SSE.
- Final event includes source objects with file path, URL, and line range.

### US-2 Receive safe refusal when evidence is weak
As a user, I want the system to refuse uncertain answers and provide best available sources so I am not misled.

Acceptance criteria:
- Low-similarity result returns refusal mode.
- Refusal includes top source snippets.

## Admin User Stories

### US-3 Trigger ingestion
As an admin, I want to trigger repository ingestion so content stays current.

Acceptance criteria:
- Admin can queue ingestion requests.
- Non-admin requests are denied with `403`.

### US-4 Tune threshold controls
As an admin, I want to update confidence threshold behavior so refusal sensitivity can be tuned.

Acceptance criteria:
- Threshold updates are auditable.
- Runtime behavior reflects updated threshold.

## Operations User Stories

### US-5 Deploy and rollback safely
As an operator, I want deploy and rollback scripts with health checks so releases are reversible.

Acceptance criteria:
- Deploy script records release metadata.
- Rollback script can target previous or explicit release.
- Post-action health checks run by default.

### US-6 Recover from backup
As an operator, I want documented backup and restore flow so I can meet RPO/RTO targets.

Acceptance criteria:
- Daily backup script produces compressed artifacts.
- Restore script supports selective full schema reset.

## Security User Stories

### US-7 Authenticate before querying
As a user, I want JWT-based authentication enforced on all endpoints so that unauthorized access is rejected.

Acceptance criteria:
- Unauthenticated requests to `/api/v1/query` return `401`.
- Admin-only endpoints return `403` when called with a non-admin token.
- Token expiry is enforced; expired tokens return `401`.

## Query Quality User Stories

### US-8 View confidence indicator in every response
As a user, I want each answer to include a confidence label (HIGH, MEDIUM, LOW) so I can calibrate how much I trust the result.

Acceptance criteria:
- Every non-refusal response event includes a `confidence` field.
- Confidence reflects the cosine similarity of top retrieved chunks.

### US-9 Receive retrieval-only response when generation budget is exhausted
As a user, I want the system to return retrieved source snippets even when the monthly token budget is exhausted so I still get value.

Acceptance criteria:
- When `budget_exhausted` flag is set, `answer_text` is absent and `sources` are still returned.
- Response includes a machine-readable `refusal_reason` of `"budget_exhausted"`.

## Observability User Stories

### US-10 View live system metrics on a dashboard
As an operator, I want a pre-configured Grafana dashboard so I can monitor query latency, error rates, and active streams without manual setup.

Acceptance criteria:
- Dashboard auto-provisions on Grafana startup via provisioning config.
- p50/p95/p99 latency panels are populated within 60 s of first query.

