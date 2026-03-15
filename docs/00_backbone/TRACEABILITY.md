# TRACEABILITY.md

## 0) Header Metadata
- Project: Smart Office Librarian (Embedlyzer)
- Architecture Version: v1.5
- Status: Active
- Last Updated: 2026-03-14
- Rule: `✅` means code exists, tests exist, tests pass, and WORK_STATUS has a green checkpoint.

## 1) Purpose Statement
This file maps each FR/NFR requirement to implementation files and verification tests.
If a requirement is not mapped here, it is not done.

## 2) Global Status Legend
- `⬜` Not started
- `🟨` In progress (partial implementation or missing tests)
- `✅` Done (implemented, tested, passing)
- `⚠️` Blocked (dependency/decision missing)

## 3) Traceability Entry Template (Required Fields)
Use this exact shape for each requirement entry:

```text
Requirement ID:
Title:
Status: ⬜ | 🟨 | ✅ | ⚠️
Implementation:
	- <file path>
Tests:
	- <test file path>
Notes:
	- <max 2 bullets>
Owner/Step:
Evidence (optional):
	- Last verified commit:
	- CI run:
	- Eval score:
```

## 4) Grouping Rules (Order)
Functional (FR):
- FR-1 Security and Auth
- FR-2 Ingestion and Lifecycle
- FR-3 RAG Pipeline
- FR-4 Index Maintenance and Versioning
- FR-5 Ops and Observability
- FR-6 Frontend
- FR-7 Multi-tenancy `[v2]`

Non-functional (NFR):
- NFR-1 Performance
- NFR-2 Scalability
- NFR-3 Reliability
- NFR-4 Security and Privacy
- NFR-5 Maintainability
- NFR-6 Observability
- NFR-7 Cost Controls

## 5) Implementation Field Rules
- Use exact file paths only (backend/frontend/infra).
- No vague text like "service implemented".

## 6) Tests Field Rules
- List exact unit/integration/evaluation test file paths.
- Tests must align with `docs/00_backbone/Backbond/TESTING.md`.

## 7) Definition of Done (Hard Rule)
Set a requirement to `✅` only if all are true:
- Listed code files exist and are implemented.
- Listed test files exist.
- Relevant tests pass.
- `WORK_STATUS.md` contains a green checkpoint for that step.

If any item is missing, status must remain `🟨`.

## 8) Partial Work Standard (`🟨`)
For `🟨`, add short missing items, for example:
- Missing integration test
- Error contract not fully wired
- Not connected to API route yet

## 9) Cross-Cutting Requirement Rule
If a requirement spans layers, list all layers explicitly:
- core + domain + api + rag + workers + infra (as applicable)
- include tests across unit and integration

## 10) Evidence Links (Optional)
Optional short evidence fields:
- Last verified commit hash
- CI run ID/link
- Evaluation score summary (P/R/F1)

## 11) Growth Control Rules
- Max 2 note bullets per requirement.
- No pasted logs.
- No pasted code.
- If this file becomes too large, split into:
	- `docs/00_backbone/TRACEABILITY_FR.md`
	- `docs/00_backbone/TRACEABILITY_NFR.md`

## 12) Agent Usage Instructions
When implementing FR/NFR-X:
1. Open this file and locate the requirement.
2. Implement listed files only.
3. Create/update listed tests.
4. Run relevant tests.
5. Update status to `🟨` or `✅`.
6. Record checkpoint in `WORK_STATUS.md`.

## 13) Future Scope Marking
For future scope items:
- Mark status as `⬜` and tag as `[v2]`.
- Exclude from MVP "must ship" set.

## Current Baseline Map (Top-Level)

### Functional (FR)
| ID | Title | Status | Implementation | Tests | Owner/Step |
|---|---|---|---|---|---|
| FR-1 | Security and Auth | ✅ | backend/app/core/security.py; backend/app/api/v1/dependencies/auth.py; backend/app/core/logging.py; backend/app/main.py | backend/tests/unit/test_api/test_auth.py; backend/tests/integration/test_auth_flow.py; backend/tests/unit/test_core/test_secrets_encryption.py; backend/tests/unit/test_core/test_logging_hygiene.py (2026-03-12: Step 42 implemented FR-1.4 pure-stdlib AES-256 secret encryption/decryption and encrypted JWT secret env resolution; implemented FR-1.5 logging/error redaction enforcement for sensitive key names and token/JWT/provider-secret patterns. Step 43 broader regression gate is green (`python -m pytest tests -v` -> 120 passed) with checkpoint commit `21b17b6` pushed to `origin/main`. Step 44 DoD evaluation confirmed all four criteria; FR-1 elevated to ✅.) | Step 44 |
| FR-2 | Ingestion and Lifecycle | ✅ | backend/app/connectors/github/client.py; backend/app/connectors/github/diff_scanner.py; backend/app/connectors/github/extractor.py; backend/app/connectors/github/ignore_rules.py; backend/app/connectors/github/validators.py; backend/app/domain/services/ingest_service.py; backend/app/workers/tasks/ingest_tasks.py | backend/tests/unit/test_connectors/test_github_client.py; backend/tests/unit/test_connectors/test_diff_scanner.py; backend/tests/unit/test_connectors/test_ignore_rules.py; backend/tests/unit/test_connectors/test_file_validator.py; backend/tests/unit/test_connectors/test_extractor.py; backend/tests/unit/domain/test_ingest_service.py; backend/tests/integration/test_ingest_flow.py (2026-03-12: Step 36 DoD evaluation confirmed all four criteria met — listed code files exist and are implemented, listed tests exist, tests pass (99/99 full regression; 32/32 FR-2 subset), and WORK_STATUS contains the green checkpoint at Steps 34-35. FR-2 elevated from 🟨 to ✅.) | Step 36 |
| FR-3 | RAG Pipeline | ✅ | backend/app/domain/services/query_service.py; backend/app/domain/services/threshold_service.py (Step 118 implemented ThresholdService.get_threshold/update_threshold with default 0.65, namespace+index_version scoping, and audit log emission — TESTING.md [REQUIRED]); backend/app/rag/stages/refusal_stage.py; backend/app/rag/pipeline.py | backend/tests/unit/domain/test_query_service.py; backend/tests/unit/domain/test_threshold_service.py (Step 118 gate: `python -m pytest backend/tests/unit/domain/test_threshold_service.py -v` -> 11 passed in 0.10s); backend/tests/unit/rag/test_refusal_stage.py; backend/tests/integration/test_query_flow.py; backend/tests/integration/test_api.py; backend/tests/integration/test_rag_pipeline.py (2026-03-12: Step 22 regression gate confirmed 25/25 green; all four DoD criteria satisfied — code files exist, test files exist, tests pass, WORK_STATUS green checkpoint present. FR-3 elevated from 🟨 to ✅.) | Step 22 |
| FR-4 | Index Maintenance and Versioning | ✅ | backend/app/domain/services/index_safety_service.py; backend/app/domain/services/query_service.py; backend/app/workers/tasks/reindex_tasks.py | backend/tests/unit/domain/test_index_safety_service.py; backend/tests/unit/domain/test_query_service.py; backend/tests/unit/test_workers/test_reindex_task.py; backend/tests/integration/test_reindex.py (2026-03-12: Step 27 DoD evaluation confirmed all four criteria met — code files exist (index_safety_service.py, query_service.py, reindex_tasks.py), test files exist (3 unit + 1 integration), tests pass (44/44 green), WORK_STATUS green checkpoint present (Step 26). FR-4 elevated from 🟨 to ✅.) | Step 27 |
| FR-5 | Ops and Observability | ✅ | backend/app/main.py; backend/app/api/v1/dependencies/rate_limit.py; backend/app/api/v1/routes/feedback_routes.py; backend/app/api/v1/routes/metrics_routes.py; backend/app/core/logging.py; backend/app/core/metrics.py | backend/tests/unit/test_api/test_rate_limit.py; backend/tests/integration/test_api.py; backend/tests/integration/test_feedback_flow.py (2026-03-12: Step 40 DoD evaluation confirmed all four criteria met — code files implemented, test files exist, tests pass (16/16 scoped and 106/106 full regression), and WORK_STATUS contains the Step 39 green checkpoint with commit 53dd80f.) | Step 40 |
| FR-6 | Frontend | ✅ | frontend/app/(query)/layout.tsx; frontend/app/(query)/page.tsx; frontend/app/(query)/loading.tsx; frontend/components/query/QueryInput.tsx; frontend/components/query/StreamingAnswer.tsx; frontend/components/query/CitationPanel.tsx; frontend/components/query/ConfidenceBadge.tsx; frontend/components/query/ThumbsFeedback.tsx; frontend/hooks/useQuery.ts; frontend/hooks/useSSEStream.ts; frontend/lib/api-client.ts; frontend/types/api.ts; frontend/types/query.ts; frontend/types/source.ts; frontend/package.json; frontend/tsconfig.json; frontend/next-env.d.ts; frontend/.eslintrc.json (2026-03-13: Step 46 finalized canonical frontend install command as `Set-Location frontend; npm install` and completed frontend validation gate with green results for `npm run test`, `npm run typecheck`, and `npm run lint`. Environment command-path quirk for `npm --prefix frontend install` is treated as non-code tooling behavior and does not block FR-6 completion. 2026-03-13: Step 47 re-ran the canonical gate from repository root (`Set-Location D:\Embedlyzer; Set-Location frontend`) and confirmed the same green outcome for `npm install`, `npm run test`, `npm run typecheck`, and `npm run lint` before checkpoint commit.) | Gate evidence: `Set-Location D:\Embedlyzer; Set-Location frontend; npm install` (success); `npm run test` (pass); `npm run typecheck` (pass); `npm run lint` (pass). | Step 47 |
| FR-7 [v2] | Multi-tenancy | ⬜ | TBD | TBD | Step 02 |

### Non-Functional (NFR)
| ID | Title | Status | Implementation | Tests | Owner/Step |
|---|---|---|---|---|---|
| NFR-1 | Performance | ✅ | evaluation/scripts/run_pqs.py; evaluation/scripts/analyze_failures.py; docs/03_engineering/BASELINES.md (Step 62 baseline harness implemented; Step 63 checkpoint commit `a1857c3`). | backend/tests/evaluation/test_latency.py; backend/tests/evaluation/test_pqs.py; evaluation/scripts/run_pqs.py; evaluation/scripts/analyze_failures.py (Step 67 checkpoint commit `8d047d2`; scoped regression gate green: 4 evaluation tests passed, analyzer overall `PASS`, p95 e2e/retrieval/TTFT under thresholds). | Step 68 |
| NFR-2 | Scalability | ✅ | backend/app/domain/services/scaling_service.py (Step 89 implemented deterministic policy for independent API and worker horizontal scaling recommendations with bounded min/max replica guards); backend/app/domain/services/concurrency_capacity_service.py (Step 101 implemented deterministic NFR-2.3 concurrency-capacity evaluation for MVP 100 active users, including bottleneck detection and replica recommendations; Step 102 re-verified gate stability on current workspace state); backend/app/domain/services/index_growth_readiness_service.py (Step 107 implemented deterministic NFR-2.2 growth-readiness checks for target chunk scale, shard requirements, and contract compatibility without core redesign; Step 109 DoD re-evaluation confirmed NFR-2 closure criteria for MVP scope). | backend/tests/unit/domain/test_scaling_service.py (Step 89 gate: `python -m pytest backend/tests/unit/domain/test_scaling_service.py -v` -> 5 passed; Step 90 rerun on same scope -> 5 passed); backend/tests/unit/domain/test_concurrency_capacity_service.py (Step 101 gate: `python -m pytest backend/tests/unit/domain/test_concurrency_capacity_service.py -v` -> 7 passed in 0.08s; Step 102 rerun -> 7 passed in 0.04s); backend/tests/unit/domain/test_index_growth_readiness_service.py (Step 107 gate: `python -m pytest backend/tests/unit/domain/test_index_growth_readiness_service.py -v` -> 7 passed in 0.09s; Step 108 regression rerun on current workspace state: `python -m pytest backend/tests/unit/domain/test_index_growth_readiness_service.py -v` -> 7 passed in 0.03s; Step 109 DoD gate: `python -m pytest backend/tests/unit/domain/test_scaling_service.py backend/tests/unit/domain/test_concurrency_capacity_service.py backend/tests/unit/domain/test_index_growth_readiness_service.py -v` -> 19 passed in 0.09s). | Step 109 |
| NFR-3 | Reliability | ✅ | infra/scripts/backup.sh; infra/scripts/restore.sh; docs/05_operations/DEPLOYMENT.md; docs/05_operations/INCIDENT_RESPONSE.md; docs/05_operations/RECOVERY_DRILL_LOG.md; backend/app/workers/tasks/reindex_tasks.py; backend/app/domain/services/query_service.py; backend/app/domain/services/incident_postmortem_policy_service.py; backend/scripts/validate_incident_postmortem.py; backend/app/domain/services/reliability_slo_service.py; backend/app/domain/services/graceful_degradation_service.py; backend/app/domain/services/recovery_drill_policy_service.py (Step 95 implemented deterministic NFR-3.1/NFR-3.3 reliability SLO instrumentation for availability exclusion semantics and ingestion retry/metadata-safety checks; Step 96 re-verified gate stability on current workspace state; Step 104 implemented deterministic NFR-3.2 graceful degradation fallback decisions with explicit retrieval-only behavior when LLM is unavailable; Step 110 implemented deterministic NFR-3.5 backup/recovery policy checks for cadence, retention, strategy, and RPO/RTO objectives; Step 115 DoD re-evaluation confirmed reliability closure criteria for NFR-3.1 through NFR-3.6.) | backend/tests/unit/test_workers/test_reindex_task.py; backend/tests/unit/domain/test_query_service.py; backend/tests/unit/domain/test_incident_postmortem_policy_service.py; backend/tests/unit/domain/test_reliability_slo_service.py; backend/tests/unit/domain/test_graceful_degradation_service.py; backend/tests/unit/domain/test_recovery_drill_policy_service.py; docs/00_backbone/Backbond/TESTING.md (Step 96 rerun: `python -m pytest backend/tests/unit/domain/test_reliability_slo_service.py -v` -> 7 passed; Step 104 gate: `python -m pytest backend/tests/unit/domain/test_graceful_degradation_service.py -v` -> 7 passed in 0.08s; Step 105 regression rerun on current workspace state: `python -m pytest backend/tests/unit/domain/test_graceful_degradation_service.py -v` -> 7 passed in 0.04s; Step 110 gate: `python -m pytest backend/tests/unit/domain/test_recovery_drill_policy_service.py -v` -> 8 passed in 0.08s; Step 111 regression rerun: `python -m pytest backend/tests/unit/domain/test_recovery_drill_policy_service.py -v` -> 8 passed in 0.04s; Step 115 DoD gate: `python -m pytest backend/tests/unit/test_workers/test_reindex_task.py backend/tests/unit/domain/test_query_service.py backend/tests/unit/domain/test_incident_postmortem_policy_service.py backend/tests/unit/domain/test_reliability_slo_service.py backend/tests/unit/domain/test_graceful_degradation_service.py backend/tests/unit/domain/test_recovery_drill_policy_service.py -v` -> 43 passed in 0.17s). | Step 115 |
| NFR-4 | Security and Privacy | ✅ | backend/app/core/security.py; backend/app/api/v1/dependencies/auth.py; backend/app/core/logging.py; backend/app/main.py; backend/app/connectors/github/client.py; backend/app/api/v1/routes/admin_routes.py; infra/caddy/Caddyfile; backend/app/db/repositories/query_logs_repo.py; backend/app/db/repositories/feedback_repo.py; backend/app/workers/tasks/purge_tasks.py (Step 80 implemented TLS/transit enforcement evidence in `infra/caddy/Caddyfile`. Step 82 implemented configurable 90-day retention purge for query logs and related feedback, including evaluation-flag exemptions and purge logging. Step 74 replay tightened bounded audit payload structure in structured logging and re-verified admin source/threshold audit emission with auth-derived actor identity.) | backend/tests/unit/test_api/test_auth.py; backend/tests/integration/test_auth_flow.py; backend/tests/unit/test_core/test_secrets_encryption.py; backend/tests/unit/test_core/test_logging_hygiene.py; backend/tests/unit/test_connectors/test_github_client.py; backend/tests/unit/test_api/test_admin_routes.py; backend/tests/integration/test_audit_logging.py; backend/tests/unit/test_infra_caddy_tls.py; backend/tests/integration/test_data_retention.py (evidence: Step 78 scoped gate -> 6 unit + 3 integration passed, commit 6ff024a; Step 81 re-ran `python -m pytest backend/tests/unit/test_infra_caddy_tls.py -v` against commit b35b4b2 -> 2 passed; Step 82 gate -> `python -m pytest backend/tests/integration/test_data_retention.py -v` -> 2 passed; Step 83 re-ran `python -m pytest backend/tests/integration/test_data_retention.py -v` against commit 33da877 -> 2 passed; Step 74 replay gate -> `python -m pytest backend/tests/unit/test_api/test_admin_routes.py -v` (8 passed) and `python -m pytest backend/tests/integration/test_audit_logging.py -v` (4 passed).) | Step 83 |
| NFR-5 | Maintainability | ✅ | backend/app/core/config.py (Step 91 implemented deterministic environment-scoped configuration snapshots and drift detection reporting); backend/app/domain/services/environment_isolation_service.py (Step 97 implemented deterministic NFR-5.3 namespace-level environment isolation enforcement for dev/staging/prod with cross-environment and unknown-namespace breach detection); backend/app/domain/services/api_stability_service.py (Step 106 implemented deterministic NFR-5.4 API stability checks for versioned public endpoints and breaking-change major-version namespace enforcement); backend/app/domain/services/deployment_safety_service.py (Step 116 implemented deterministic NFR-5.5 deployment safety checks for production integration/evaluation gate readiness and backward-compatible rolling migration policy); docs/00_backbone/Backbond/TESTING.md; docs/00_backbone/WORK_STATUS.md | backend/tests/unit/test_core/test_config.py (Step 91 gate: `python -m pytest backend/tests/unit/test_core/test_config.py -v` -> 5 passed; Step 92 rerun -> 5 passed); backend/tests/unit/domain/test_environment_isolation_service.py (Step 97 gate: `python -m pytest backend/tests/unit/domain/test_environment_isolation_service.py -v` -> 8 passed in 0.08s; Step 98 rerun -> 8 passed in 0.03s); backend/tests/unit/domain/test_api_stability_service.py (Step 106 gate: `python -m pytest backend/tests/unit/domain/test_api_stability_service.py -v` -> 7 passed in 0.07s); backend/tests/unit/domain/test_deployment_safety_service.py (Step 116 gate: `python -m pytest backend/tests/unit/test_core/test_config.py backend/tests/unit/domain/test_environment_isolation_service.py backend/tests/unit/domain/test_api_stability_service.py backend/tests/unit/domain/test_deployment_safety_service.py -v` -> 28 passed in 0.16s; Step 117 maintainability DoD gate: `python -m pytest backend/tests/unit/test_core/test_config.py backend/tests/unit/domain/test_environment_isolation_service.py backend/tests/unit/domain/test_api_stability_service.py backend/tests/unit/domain/test_deployment_safety_service.py -v` -> 28 passed in 0.16s); docs/00_backbone/Backbond/TESTING.md (deterministic parity checks). | Step 117 |
| NFR-6 | Observability | ✅ | backend/app/core/metrics.py; backend/app/core/telemetry.py; backend/app/api/v1/routes/metrics_routes.py; backend/app/main.py; infra/prometheus/prometheus.yml; infra/prometheus/alerts.yml (2026-03-13: Step 50 implemented canonical `librarian_*` metrics family support and query-path telemetry emission; Step 54 added OpenTelemetry bootstrap fallback (`setup_telemetry`) and Prometheus scrape/alert configuration.) | backend/tests/unit/test_api/test_metrics_routes.py; backend/tests/unit/test_core/test_telemetry.py; backend/tests/integration/test_api.py (Step 55 green checkpoint evidence: `python -m pytest tests/unit -v` -> 90 passed; `python -m pytest tests/integration -v` -> 41 passed; checkpoint commit `afdc0fd`). | Step 56 |
| NFR-7 | Cost Controls | ✅ | backend/app/domain/services/cost_service.py; backend/app/domain/services/query_service.py (Step 87 implemented monthly spend-cap evaluation and query fallback to retrieval-only when projected cost exceeds budget cap.); backend/app/domain/services/token_budget_service.py (Step 99 implemented deterministic NFR-7.2 context/output token budget enforcement with explicit violation reasons and capped allowed token outputs; Step 100 re-verified gate stability on current workspace state; Step 103 DoD review confirmed closure criteria). | backend/tests/unit/domain/test_cost_service.py; backend/tests/unit/domain/test_query_service.py (Step 87 gate: `python -m pytest backend/tests/unit/domain/test_cost_service.py backend/tests/unit/domain/test_query_service.py -v` -> 11 passed; Step 88 rerun on same scope -> 11 passed); backend/tests/unit/domain/test_token_budget_service.py (Step 99 gate: `python -m pytest backend/tests/unit/domain/test_token_budget_service.py -v` -> 8 passed in 0.07s; Step 100 rerun -> 8 passed in 0.03s; Step 103 rerun with cost/query/token suite -> 19 passed in 0.12s). | Step 103 |

## What TRACEABILITY Is NOT
- Not long requirement descriptions (use REQUIREMENTS.md).
- Not implementation algorithm details.
- Not runbook procedures.
- Not testing instructions (use TESTING.md).

TRACEABILITY is a map, not a manual.
