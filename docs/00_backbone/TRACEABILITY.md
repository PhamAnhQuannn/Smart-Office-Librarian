# TRACEABILITY.md

## 0) Header Metadata
- Project: Smart Office Librarian (Embedlyzer)
- Architecture Version: v1.5
- Status: Active
- Last Updated: 2026-03-12 22:40
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
| FR-1 | Security and Auth | 🟨 | backend/app/core/security.py; backend/app/api/v1/dependencies/auth.py; backend/app/core/logging.py; backend/app/main.py | backend/tests/unit/test_api/test_auth.py; backend/tests/integration/test_auth_flow.py; backend/tests/unit/test_core/test_secrets_encryption.py; backend/tests/unit/test_core/test_logging_hygiene.py (2026-03-12: Step 42 implemented FR-1.4 pure-stdlib AES-256 secret encryption/decryption and encrypted JWT secret env resolution; implemented FR-1.5 logging/error redaction enforcement for sensitive key names and token/JWT/provider-secret patterns. Step 43 broader regression gate is green (`python -m pytest tests -v` -> 120 passed) and checkpoint artifacts were committed/pushed. Pending Step 44 DoD evaluation.) | Step 44 |
| FR-2 | Ingestion and Lifecycle | ✅ | backend/app/connectors/github/client.py; backend/app/connectors/github/diff_scanner.py; backend/app/connectors/github/extractor.py; backend/app/connectors/github/ignore_rules.py; backend/app/connectors/github/validators.py; backend/app/domain/services/ingest_service.py; backend/app/workers/tasks/ingest_tasks.py | backend/tests/unit/test_connectors/test_github_client.py; backend/tests/unit/test_connectors/test_diff_scanner.py; backend/tests/unit/test_connectors/test_ignore_rules.py; backend/tests/unit/test_connectors/test_file_validator.py; backend/tests/unit/test_connectors/test_extractor.py; backend/tests/unit/domain/test_ingest_service.py; backend/tests/integration/test_ingest_flow.py (2026-03-12: Step 36 DoD evaluation confirmed all four criteria met — listed code files exist and are implemented, listed tests exist, tests pass (99/99 full regression; 32/32 FR-2 subset), and WORK_STATUS contains the green checkpoint at Steps 34-35. FR-2 elevated from 🟨 to ✅.) | Step 36 |
| FR-3 | RAG Pipeline | ✅ | backend/app/domain/services/query_service.py; backend/app/rag/stages/refusal_stage.py; backend/app/rag/pipeline.py | backend/tests/unit/domain/test_query_service.py; backend/tests/unit/rag/test_refusal_stage.py; backend/tests/integration/test_query_flow.py; backend/tests/integration/test_api.py; backend/tests/integration/test_rag_pipeline.py (2026-03-12: Step 22 regression gate confirmed 25/25 green; all four DoD criteria satisfied — code files exist, test files exist, tests pass, WORK_STATUS green checkpoint present. FR-3 elevated from 🟨 to ✅.) | Step 22 |
| FR-4 | Index Maintenance and Versioning | ✅ | backend/app/domain/services/index_safety_service.py; backend/app/domain/services/query_service.py; backend/app/workers/tasks/reindex_tasks.py | backend/tests/unit/domain/test_index_safety_service.py; backend/tests/unit/domain/test_query_service.py; backend/tests/unit/test_workers/test_reindex_task.py; backend/tests/integration/test_reindex.py (2026-03-12: Step 27 DoD evaluation confirmed all four criteria met — code files exist (index_safety_service.py, query_service.py, reindex_tasks.py), test files exist (3 unit + 1 integration), tests pass (44/44 green), WORK_STATUS green checkpoint present (Step 26). FR-4 elevated from 🟨 to ✅.) | Step 27 |
| FR-5 | Ops and Observability | ✅ | backend/app/main.py; backend/app/api/v1/dependencies/rate_limit.py; backend/app/api/v1/routes/feedback_routes.py; backend/app/api/v1/routes/metrics_routes.py; backend/app/core/logging.py; backend/app/core/metrics.py | backend/tests/unit/test_api/test_rate_limit.py; backend/tests/integration/test_api.py; backend/tests/integration/test_feedback_flow.py (2026-03-12: Step 40 DoD evaluation confirmed all four criteria met — code files implemented, test files exist, tests pass (16/16 scoped and 106/106 full regression), and WORK_STATUS contains the Step 39 green checkpoint with commit 53dd80f.) | Step 40 |
| FR-6 | Frontend | ⬜ | TBD | TBD | Step 02 |
| FR-7 [v2] | Multi-tenancy | ⬜ | TBD | TBD | Step 02 |

### Non-Functional (NFR)
| ID | Title | Status | Implementation | Tests | Owner/Step |
|---|---|---|---|---|---|
| NFR-1 | Performance | ⬜ | TBD | TBD | Step 02 |
| NFR-2 | Scalability | ⬜ | TBD | TBD | Step 02 |
| NFR-3 | Reliability | ⬜ | TBD | TBD | Step 02 |
| NFR-4 | Security and Privacy | ⬜ | TBD | TBD | Step 02 |
| NFR-5 | Maintainability | 🟨 | docs/00_backbone/Backbond/TESTING.md; docs/00_backbone/WORK_STATUS.md | docs/00_backbone/Backbond/TESTING.md (deterministic parity checks) | Step 03 |
| NFR-6 | Observability | ⬜ | TBD | TBD | Step 02 |
| NFR-7 | Cost Controls | ⬜ | TBD | TBD | Step 02 |

## What TRACEABILITY Is NOT
- Not long requirement descriptions (use REQUIREMENTS.md).
- Not implementation algorithm details.
- Not runbook procedures.
- Not testing instructions (use TESTING.md).

TRACEABILITY is a map, not a manual.
