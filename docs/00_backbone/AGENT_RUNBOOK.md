# AGENT_RUNBOOK.md

## 0) Header Metadata
- Project: Smart Office Librarian (Embedlyzer)
- Architecture Version: v1.5 (production baseline)
- Document Status: Active
- Last Updated: 2026-03-12
- Owner: Engineering Team
- Scope: This runbook governs implementation and testing workflow for this repository.

## 1) Purpose and Non-Negotiable Goals
This runbook defines the only allowed workflow for agents implementing code in this repo.
All sessions must follow this workflow to keep changes small, testable, and traceable.

Primary goals:
- Prevent drift from canonical decisions.
- Ensure docs-to-code alignment.
- Keep context small and focused.
- Require tests and traceability for every completed step.

## 2) Canonical Source of Truth Rules
Priority order for conflicts:
1. `docs/00_backbone/Backbond/DECISIONS.md`
2. `docs/00_backbone/Backbond/REQUIREMENTS.md`
3. `docs/00_backbone/Backbond/TESTING.md`
4. `docs/00_backbone/AGENT_RUNBOOK.md`
5. Other docs and notes

Conflict rule:
- If conflict is found, stop implementation and log blocker in `docs/00_backbone/WORK_STATUS.md`.

## 3) Context Discipline Rules
### 3.1 Always-Read Set (every session)
- `docs/00_backbone/Backbond/DECISIONS.md`
- `docs/00_backbone/WORK_STATUS.md`
- `docs/00_backbone/TRACEABILITY.md` (active requirement section only)
- `docs/00_backbone/AGENT_RUNBOOK.md`

### 3.2 Section-Read Set (only relevant sections)
- `REQUIREMENTS.md`: only target FR/NFR.
- `TESTING.md`: only tests tied to target FR/NFR.
- `OPERATIONS.md` / `ARCHITECTURE.md`: only sections required by current step.

### 3.3 Never-Read-by-Default
- Large datasets
- Full evaluation result dumps
- Full repo scans
- `migrations/` unless working on migrations

### 3.4 One Session = One Requirement
- Each session targets exactly one requirement or sub-requirement.
- No multi-feature sessions.

## 4) Working Unit Definition (Step Size)
A valid step is one of:
- One service/module
- One endpoint
- One worker task
- One requirement/sub-requirement

A step must include:
- Implementation
- Tests for that scope
- `TRACEABILITY.md` update

Completion rule:
- A step is not complete unless required unit tests pass.

## 5) Mandatory Workflow Loop (Session Template)
### 5.1 READ
- Read always-read docs.
- Read only required sections for target requirement.
- Read only directly involved code files.

### 5.2 PLAN (small)
- List files to modify/create.
- List tests to add/update.
- Confirm expected behavior from DECISIONS and REQUIREMENTS.

### 5.3 IMPLEMENT
- Edit only planned files.
- No out-of-scope refactors.
- Do not move folders unless required.

### 5.4 TEST
- Run smallest relevant unit tests first.
- Run relevant integration tests when required.
- Do not mark done unless tests are green.

### 5.5 UPDATE DOCS
- Update `TRACEABILITY.md` mapping/status.
- Update `WORK_STATUS.md` stable checkpoint.
- Add `RESUME FROM HERE` marker.

### 5.6 OUTPUT CHECKPOINT MESSAGE
Output must include:
- What changed
- Tests run and results
- Next step pointer

## 6) WORK_STATUS Update Rules (Hard)
Update `WORK_STATUS.md` only at:
1. Start of step (set in-progress)
2. End of step (only after tests green)
3. Blocked state (log blocker and reason)

Rules:
- Never update `WORK_STATUS.md` for micro-edits.
- `WORK_STATUS.md` tracks stable checkpoints only.

## 7) Traceability Rules (Hard)
For every implemented requirement, map:
- Requirement ID
- Code file(s)
- Test file(s)
- Status (`⬜`, `🟨`, `✅`)

Status meaning:
- `✅`: code exists, tests exist, tests pass
- `🟨`: partial implementation; list missing items
- `⬜`: not started

## 8) Hard Invariants (Do Not Break)
- RAG purity: no DB imports in `app/rag/**`.
- RBAC filter: `(visibility == "public") OR (allowed_user_ids contains user.id)`.
- Threshold rule: `cosine_score >= threshold` passes; otherwise refusal.
- Refusal contract: HTTP 200 with `refusal_reason` and top-3 sources.
- 409 mismatch contract: include `error_code` and expected vs received fields.
- Chunking constants: 512 max tokens, 50 overlap.
- Retrieval constants: `top_k=20`, `top_n=5`.
- Token budgets: context 1500, response 500.
- Rate limits: 50/hour, concurrency 5.
- Atomicity: Source metadata updates only after successful ingestion/reindex validation.

## 9) Naming and Location Conventions
- API routes: `backend/app/api/v1/routes/`
- Domain services: `backend/app/domain/services/`
- DB repositories: `backend/app/db/repositories/`
- Unit tests mirror modules under `backend/tests/unit/`
- RAG tests: `backend/tests/unit/rag/`
- Integration tests: `backend/tests/integration/`

Rule:
- Do not create new folders unless structure requires it.

## 10) Test Execution Rules
Minimum per step:
- Run relevant unit tests for changed module(s).
- Run relevant integration tests for endpoint/contract changes.

If contracts/invariants are touched:
- Run full relevant suite for that area.

Test quality rule:
- Unit tests must not call external APIs.

Suggested commands:
```bash
pytest tests/unit/<scope> -v
pytest tests/integration/<scope> -v
```

## 11) Commit and PR Discipline (Recommended)
- Prefer one step per commit.
- Commit message format examples:
	- `feat(rag): implement refusal stage`
	- `test(domain): add index safety mismatch tests`
- Require CI green before merge.

## 12) Agent Prompt Template (Copy/Paste)
Use this prompt:

```text
Read first: AGENT_RUNBOOK.md, WORK_STATUS.md, DECISIONS.md, and active TRACEABILITY.md section.
Target requirement: <FR/NFR ID>.
Implement only these files: <list>.
Add/update tests: <list>.
Run tests: <exact commands>.
Update WORK_STATUS.md and TRACEABILITY.md.
Print final line: RESUME FROM HERE -> <next file/step>.
```

## 13) Stop Conditions (Safety Rails)
Stop and log blocker if:
- DECISIONS conflicts with REQUIREMENTS or TESTING.
- A required architectural choice is undefined.
- Tests require missing design details.
- Scope expands beyond one requirement step.

When stopped:
- Do not invent architecture.
- Record blocker in `WORK_STATUS.md` with exact conflict and needed decision.
