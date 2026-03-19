# Multi-Tenant Self-Serve Migration Plan
> **Goal**: Transform Embedlyzer from single-tenant internal tool → multi-tenant SaaS platform where any user can self-register, connect their own repos, and query their own isolated knowledge base.

**Status Legend**: `[ ]` = Not started · `[x]` = Done · `[~]` = In progress

---

## 📋 Table of Contents
1. [Phase 1 — Data Model Foundation](#phase-1--data-model-foundation)
2. [Phase 2 — Auth: Self-Registration](#phase-2--auth-self-registration)
3. [Phase 3 — Workspace-Scoped Ingestion](#phase-3--workspace-scoped-ingestion)
4. [Phase 4 — Workspace-Scoped Query](#phase-4--workspace-scoped-query)
5. [Phase 5 — Per-User Resource Quotas](#phase-5--per-user-resource-quotas)
6. [Phase 6 — Frontend: Signup & Sources Dashboard](#phase-6--frontend-signup--sources-dashboard)
7. [Phase 7 — Frontend: Workspace-Aware Query UI](#phase-7--frontend-workspace-aware-query-ui)
8. [Phase 8 — Infra & Deployment Adjustments](#phase-8--infra--deployment-adjustments)
9. [Phase 9 — Evaluation & Tests Update](#phase-9--evaluation--tests-update)
10. [Phase 10 — Admin Panel Adjustments](#phase-10--admin-panel-adjustments)
11. [GitHub Push Checkpoints](#github-push-checkpoints)

---

## Phase 1 — Data Model Foundation
> **What**: Add `Workspace` model. Add `workspace_id` foreign key to `Source`, `Chunk`, `IngestRun`. Re-purpose Pinecone namespaces from index-version slots → per-workspace isolators.

### 1.1 — New ORM model: `WorkspaceModel`
**File**: `backend/app/db/models.py`
- [ ] Add `WorkspaceModel` class with fields:
  - `id` (UUID PK)
  - `owner_id` (FK → `users.id`, `ondelete=CASCADE`)
  - `slug` (unique, lowercase, URL-safe — used as Pinecone namespace)
  - `display_name`
  - `max_chunks` (int, default 5000)
  - `max_sources` (int, default 20)
  - `monthly_query_cap` (int, default 500)
  - `created_at`, `updated_at`
- [ ] Add `workspace: Mapped["WorkspaceModel"]` relationship back-ref on `UserModel`

### 1.2 — Add `workspace_id` FK to `SourceModel`
**File**: `backend/app/db/models.py`
- [ ] Add `workspace_id: Mapped[str]` → FK `workspaces.id` `ondelete=CASCADE`, `nullable=False`
- [ ] Remove `visibility` column (replaced by workspace-level isolation)
- [ ] Update `SourceModel` relationship to include workspace

### 1.3 — Add `workspace_id` FK to `IngestRunModel`
**File**: `backend/app/db/models.py`
- [ ] Add `workspace_id: Mapped[str]` → FK `workspaces.id` `ondelete=CASCADE`, `nullable=True`

### 1.4 — Update `ChunkModel` namespace to be workspace slug
**File**: `backend/app/db/models.py`
- [ ] `namespace` column stays but its value is now always `workspace.slug` (not `"dev"`)
- [ ] Add comment clarifying semantic

### 1.5 — New Alembic migration
**File**: `backend/app/db/migrations/versions/0003_add_workspaces.py`
- [ ] Create `workspaces` table
- [ ] Add `workspace_id` column to `sources` (nullable first, then backfill, then NOT NULL)
- [ ] Add `workspace_id` column to `ingest_runs` (nullable)
- [ ] Drop `visibility` column from `sources`
- [ ] Add index on `workspaces.owner_id`
- [ ] Add index on `sources.workspace_id`
- [ ] Downgrade: reverse all

### 1.6 — New repository: `WorkspacesRepository`
**File**: `backend/app/db/repositories/workspaces_repo.py` *(new file)*
- [ ] `create(*, owner_id, display_name) -> WorkspaceModel` — auto-generates `slug = owner_id[:8]`
- [ ] `get_by_owner(owner_id) -> WorkspaceModel | None`
- [ ] `get_by_id(workspace_id) -> WorkspaceModel | None`
- [ ] `get_by_slug(slug) -> WorkspaceModel | None`

### 1.7 — Update `SourcesRepository`
**File**: `backend/app/db/repositories/sources_repo.py` *(if exists, else create)*
- [ ] `list_by_workspace(workspace_id, *, limit, offset)` method
- [ ] `count_by_workspace(workspace_id) -> int`

---

## Phase 2 — Auth: Self-Registration
> **What**: Allow any visitor to create an account. Auto-create a workspace for them on signup.

### 2.1 — Registration endpoint
**File**: `backend/app/api/v1/routes/auth_routes.py`
- [ ] Add `POST /auth/register` endpoint
  - Accept `{ email, password }` (Pydantic model `RegisterRequest`)
  - Validate email format (regex, no leading/trailing whitespace)
  - Validate password minimum length ≥ 8 chars
  - Check `UsersRepository.get_by_email()` — return `409 CONFLICT` if already exists
  - Hash password with `bcrypt.hashpw()`
  - `UsersRepository.create(email, hashed_password, role="user")`
  - Auto-create `WorkspaceModel` for new user via `WorkspacesRepository.create()`
  - Issue JWT via `issue_jwt_token()` (same as login)
  - Return `201` with `TokenResponse`
- [ ] **Security**: rate limit registration endpoint (5 attempts / 15 min per IP) — add to middleware
- [ ] **Security**: never leak whether email already exists in error detail for login (already done); registration can say "email already registered"

### 2.2 — Router registration
**File**: `backend/app/api/v1/router.py`
- [ ] Register new `/auth/register` route (it lives in `auth_routes.py` — no import change needed if router is already included)

### 2.3 — `UsersRepository`: ensure `create` hashes password correctly
**File**: `backend/app/db/repositories/users_repo.py`
- [ ] Verify `create()` stores bcrypt hash, not plaintext
- [ ] Remove `INSECURE-PLAIN:` fallback from `_verify_password` in `auth_routes.py` (was only for seed_db)

### 2.4 — Update JWT: embed `workspace_id` claim
**File**: `backend/app/core/security.py`
- [ ] Add `workspace_id: str` param to `issue_jwt_token()`
- [ ] Include `"workspace_id"` in JWT payload dict
- [ ] Update `AuthenticatedUser` dataclass: add `workspace_id: str` field
- [ ] Update `get_current_user()` in `auth.py`: extract `workspace_id` from claims

**File**: `backend/app/api/v1/dependencies/auth.py`
- [ ] Pass `workspace_id` from claims → `AuthenticatedUser`

**File**: `backend/app/api/v1/routes/auth_routes.py`
- [ ] Pass `workspace_id` from DB to `issue_jwt_token()` after creating/fetching workspace

### 2.5 — Frontend type: add `workspace_id` to `AuthUser`
**File**: `frontend/types/user.ts`
- [ ] Add `workspace_id: string` field to `AuthUser` interface

---

## Phase 3 — Workspace-Scoped Ingestion
> **What**: Regular users can trigger ingestion into their own workspace. Namespace = workspace slug. Quota enforced before starting.

### 3.1 — Remove admin-only gate from ingest endpoint
**File**: `backend/app/api/v1/routes/ingest_routes.py`
- [ ] Delete the `if not user.is_admin: return 403` block
- [ ] Replace with: resolve workspace from `user.workspace_id`
- [ ] Validate `WorkspacesRepository.get_by_id(user.workspace_id)` exists and belongs to user
- [ ] Enforce source quota: `SourcesRepository.count_by_workspace(workspace_id) >= workspace.max_sources` → return `429 QUOTA_EXCEEDED`
- [ ] Enforce chunk quota check pre-flight (estimate: count existing `ChunkModel` rows for workspace)
- [ ] Set `namespace = workspace.slug` in the job record (override any client-sent namespace)
- [ ] Set `workspace_id` on job record

### 3.2 — Update ingest job record schema
**File**: `backend/app/api/v1/routes/ingest_routes.py`
- [ ] Add `workspace_id` and `namespace` to `record` dict stored in `ingest_jobs`
- [ ] Remove `requested_by` (replace with `workspace_id`)

### 3.3 — Update `IngestRunModel` creation
**File**: `backend/app/workers/tasks/ingest_tasks.py`
- [ ] Pass `workspace_id` when creating `IngestRunModel`
- [ ] Use `workspace.slug` as Pinecone upsert namespace

### 3.4 — Update `SourceModel` creation in ingestion
**File**: `backend/app/workers/tasks/ingest_tasks.py` (or `ingest_service.py`)
- [ ] Set `workspace_id` on every `SourceModel` created during indexing
- [ ] Remove `visibility` field assignment

### 3.5 — Update purge tasks to be workspace-scoped
**File**: `backend/app/workers/tasks/purge_tasks.py`
- [ ] Ensure purge queries filter by `workspace_id` so a user can only purge their own data

### 3.6 — Ingest route: accept `source_url` instead of raw `repo`
**File**: `backend/app/api/v1/routes/ingest_routes.py`
- [ ] Rename `payload["repo"]` → `payload["source_url"]` for GitHub URLs
- [ ] Validate URL is a GitHub HTTPS URL (use existing `validators.py`)
- [ ] Keep `branch` and `strategy` params

---

## Phase 4 — Workspace-Scoped Query
> **What**: Every user's query is automatically scoped to their workspace's Pinecone namespace. No client can send a namespace override.

### 4.1 — Remove client-controlled namespace from query endpoint
**File**: `backend/app/api/v1/routes/query_routes.py`
- [ ] Delete `namespace = str(payload.get("namespace") or "dev")` line
- [ ] Replace with: `namespace = user.workspace_id` → lookup workspace slug from DB or JWT claim
- [ ] Optionally cache workspace slug in JWT claim (added in Phase 2.4)

### 4.2 — Remove client-controlled `index_version` from query endpoint
**File**: `backend/app/api/v1/routes/query_routes.py`
- [ ] `index_version` should come from workspace record, not client payload
- [ ] Remove `int(payload.get("index_version") or 1)` line

### 4.3 — RBAC filter: always scope by workspace namespace
**File**: `backend/app/api/v1/routes/query_routes.py`
- [ ] Remove the `rbac_filter = {"visibility": "public"} if not user.is_admin else None` line
- [ ] Replace with: `rbac_filter = None` (namespace isolation via Pinecone namespace is the enforcement layer)
- [ ] Admins query by explicit workspace_id param (separate admin query route or namespace param)

### 4.4 — Update `QueryRequest` model
**File**: `backend/app/domain/services/query_service.py`
- [ ] Add `workspace_id: str` to `QueryRequest`
- [ ] Remove `rbac_filter` (or keep as optional override for future admin use)

### 4.5 — Update `RBACService`
**File**: `backend/app/domain/services/rbac_service.py`
- [ ] Replace namespace-list-based access control with workspace slug check
- [ ] `can_access_namespace(user, namespace)` → returns `True` if `namespace == user.workspace_id_slug`

---

## Phase 5 — Per-User Resource Quotas
> **What**: Each workspace has limits: `max_sources`, `max_chunks`, `monthly_query_cap`. Enforce at API level.

### 5.1 — Query quota enforcement
**File**: `backend/app/api/v1/routes/query_routes.py`
- [ ] Before executing query: load workspace, check `query_count_this_month < monthly_query_cap`
- [ ] Increment per-workspace query counter in Redis (`workspace:{id}:queries:{YYYY-MM}`)
- [ ] Return `429 QUOTA_EXCEEDED` with clear message if over cap

### 5.2 — `CostService`: per-workspace token budget
**File**: `backend/app/domain/services/cost_service.py`
- [ ] Replace global `monthly_token_budget` with per-workspace override
- [ ] Accept `workspace_id` in budget check
- [ ] Store per-workspace token usage in Redis (`workspace:{id}:tokens:{YYYY-MM}`)

### 5.3 — Workspace quota API endpoint
**File**: `backend/app/api/v1/routes/workspace_routes.py` *(new file)*
- [ ] `GET /workspace/me` — returns current user's workspace: slug, quotas, current usage (sources count, chunk count, queries this month)
- [ ] `GET /workspace/sources` — list all sources in workspace (file_path, repo, status, created_at)
- [ ] `DELETE /workspace/sources/{source_id}` — delete a source and its vectors from Pinecone + DB

### 5.4 — Register workspace router
**File**: `backend/app/api/v1/router.py`
- [ ] `api_router.include_router(workspace_router)`

---

## Phase 6 — Frontend: Signup & Sources Dashboard
> **What**: Signup page + authenticated user dashboard ("My Sources") to add/view/delete repos.

### 6.1 — Signup page
**File**: `frontend/app/(auth)/signup/page.tsx` *(new file)*
- [ ] Form: email + password + confirm password
- [ ] Client-side validation: email format, password ≥ 8 chars, passwords match
- [ ] On submit: `POST /api/v1/auth/register` via `api-client.ts`
- [ ] On success: `setToken(token)` → `router.replace("/")`
- [ ] On 409: show "Email already registered. Log in instead."
- [ ] Link from login page: "Don't have an account? Sign up"

### 6.2 — Add `postRegister` to API client
**File**: `frontend/lib/api-client.ts`
- [ ] Add `postRegister(email, password): Promise<{ access_token: string }>` function
- [ ] Follow same pattern as existing `postFeedback`

### 6.3 — Update login page: add signup link
**File**: `frontend/app/(auth)/login/page.tsx`
- [ ] Add "Don't have an account? Sign up →" link pointing to `/signup`

### 6.4 — Sources dashboard page
**File**: `frontend/app/(query)/sources/page.tsx` *(new file)*
- [ ] Show workspace info: slug, quota bars (sources used / max, chunks used / max, queries this month / cap)
- [ ] List all connected sources: repo name, file count, status badge (indexed/pending/failed), last indexed date
- [ ] "Add Source" button → opens `AddSourceModal`
- [ ] Per-source "Delete" button with confirmation

### 6.5 — Add Source modal component
**File**: `frontend/components/workspace/AddSourceModal.tsx` *(new file)*
- [ ] Input: GitHub repo URL (validate `https://github.com/` prefix client-side)
- [ ] Select: branch (`main` default)
- [ ] Select: strategy (`full` / `incremental`)
- [ ] Submit → `POST /api/v1/ingest`
- [ ] Success: close modal, refetch sources list
- [ ] Quota exceeded: show friendly error

### 6.6 — Workspace API client functions
**File**: `frontend/lib/api-client.ts`
- [ ] `getWorkspaceMe(authToken): Promise<WorkspaceInfo>` → `GET /api/v1/workspace/me`
- [ ] `getWorkspaceSources(authToken): Promise<Source[]>` → `GET /api/v1/workspace/sources`
- [ ] `deleteWorkspaceSource(sourceId, authToken): Promise<void>` → `DELETE /api/v1/workspace/sources/{id}`
- [ ] `postIngest(payload, authToken): Promise<IngestJob>` → `POST /api/v1/ingest`

### 6.7 — Workspace types
**File**: `frontend/types/workspace.ts` *(new file)*
- [ ] `WorkspaceInfo` interface (slug, display_name, max_sources, max_chunks, monthly_query_cap, current usage counts)
- [ ] `Source` interface (id, repo, file_path, source_url, status, created_at)
- [ ] `IngestJob` interface (job_id, repo, status)

### 6.8 — Sidebar: add "My Sources" nav link
**File**: `frontend/components/layout/Sidebar.tsx`
- [ ] Add `{ id: "sources", label: "My Sources", href: "/sources", icon: Database }` to `USER_NAV`
- [ ] Remove hardcoded suggestion strings that reference old internal content ("company wiki", "runbooks")

### 6.9 — Update hero copy on query page
**File**: `frontend/app/(query)/page.tsx`
- [ ] Change hero subtitle from internal-tool copy to product copy:
  - Title: `"Ask your codebase anything."`
  - Subtitle: `"Connect a GitHub repo, then ask questions and get grounded answers with source citations."`
- [ ] Update suggestion chips to be generic:
  - `"How does authentication work?"`
  - `"What does the ingestion pipeline do?"`
  - `"Where is the database configured?"`
- [ ] If user has no sources yet: show CTA banner "You haven't connected any repos yet. → Add your first source"

---

## Phase 7 — Frontend: Workspace-Aware Query UI
> **What**: Query is now scoped automatically — no namespace field needed. Remove any admin-only concepts from user-facing UI.

### 7.1 — Update `useQuery` hook: remove namespace param
**File**: `frontend/hooks/useQuery.ts`
- [ ] Remove any `namespace` field from query payload sent to `/api/v1/query`
- [ ] Remove `index_version` field from query payload (backend resolves from workspace)

### 7.2 — Update `QueryInput` if it exposes namespace
**File**: `frontend/components/query/QueryInput.tsx`
- [ ] Remove any namespace or index_version inputs if present

### 7.3 — No-sources empty state
**File**: `frontend/app/(query)/page.tsx`
- [ ] If `GET /workspace/sources` returns empty array → show empty state with "Add Source" button instead of suggestion chips

---

## Phase 8 — Infra & Deployment Adjustments
> **What**: Environment variables, Docker, seed scripts, and Caddy updates for multi-tenant mode.

### 8.1 — Remove `DEFAULT_NAMESPACE=dev` from env
**File**: `infra/docker/docker-compose.yml`
- [ ] Remove `DEFAULT_NAMESPACE` env var (namespace now = workspace slug, derived at runtime)

**File**: `backend/app/core/config.py`
- [ ] Remove `default_namespace` field (or keep with deprecation comment; it will be unused)

### 8.2 — Add `REGISTRATION_ENABLED` feature flag
**File**: `infra/docker/docker-compose.yml`
- [x] Add `REGISTRATION_ENABLED=true` env var
**File**: `backend/app/api/v1/routes/auth_routes.py`
- [x] Check `os.environ.get("REGISTRATION_ENABLED", "true")` at start of register endpoint; return `403 FEATURE_DISABLED` if false

### 8.3 — Update seed_db.py
**File**: `backend/scripts/seed_db.py`
- [ ] Remove `INSECURE-PLAIN:` password hashing
- [ ] Auto-create a `WorkspaceModel` for each seeded user
- [ ] Use bcrypt for passwords

### 8.4 — Migration runner in Docker entrypoint
**File**: `infra/docker/Dockerfile.api`
- [ ] Confirm `alembic upgrade head` runs before `uvicorn` start (already present — verify)
- [ ] Ensure migration `0003_add_workspaces.py` is included

### 8.5 — Caddy config: no changes needed
**File**: `infra/caddy/Caddyfile`
- [ ] No changes — `/api/*` → FastAPI still applies. Confirm `/api/v1/workspace/*` is not blocked.

### 8.6 — Prometheus metrics: add workspace label
**File**: `backend/app/core/metrics.py`
- [ ] Add `workspace_id` label to `QUERY_LATENCY`, `FEEDBACK_TOTAL` metrics (optional — low priority)

---

## Phase 9 — Evaluation & Tests Update

### 9.1 — Update unit tests for auth
**File**: `backend/tests/unit/` *(find existing auth tests)*
- [x] Add `test_register_success` — creates user + workspace, returns 201 + JWT
- [x] Add `test_register_duplicate_email` — returns 409
- [x] Add `test_register_short_password` — returns 422
- [x] Update `test_login` — ensure workspace_id appears in JWT claims

### 9.2 — Update unit tests for query route
**File**: `backend/tests/unit/` *(find existing query tests)*
- [ ] Remove tests that pass `namespace` in client payload
- [ ] Add test: namespace derived from JWT workspace_id claim

### 9.3 — Update unit tests for ingest route
**File**: `backend/tests/unit/` *(find existing ingest tests)*
- [x] Remove admin-only gate test (or update it to test quota enforcement instead)
- [x] Add test: quota exceeded returns 429

### 9.4 — Integration test: full self-serve flow
**File**: `backend/tests/integration/test_self_serve_flow.py` *(new file)*
- [ ] Register → Login → Ingest → Query → Delete Source full round-trip test

### 9.5 — Update golden questions dataset
**File**: `evaluation/datasets/golden_questions_v1.json`
- [ ] Replace internal-specific questions with generic code-question templates
- [ ] Add `workspace_id` field to each entry for evaluation runs

### 9.6 — Update evaluation scripts
**File**: `evaluation/scripts/evaluate_golden_questions.py`
- [ ] Accept `--workspace-id` arg
- [ ] Pass workspace namespace when calling query endpoint

**File**: `backend/scripts/evaluate_golden_questions.py`
- [ ] Same workspace-id param update

---

## Phase 10 — Admin Panel Adjustments
> **What**: Admins now manage workspaces, not just a single global index. Admin ingest still works but targets a specific workspace.

### 10.1 — Admin: list all workspaces
**File**: `backend/app/api/v1/routes/admin_routes.py`
- [ ] `GET /admin/workspaces` — list all workspaces with owner email, source count, chunk count, query count
- [ ] `DELETE /admin/workspaces/{workspace_id}` — delete workspace + cascade sources, chunks, Pinecone namespace

### 10.2 — Admin: ingest now requires workspace_id
**File**: `backend/app/api/v1/routes/ingest_routes.py`
- [x] When `user.is_admin`: allow passing explicit `workspace_id` in payload (for cross-workspace admin ops)
- [x] Default: use admin's own workspace

### 10.3 — Admin frontend: workspace list page
**File**: `frontend/app/admin/workspaces/page.tsx` *(new file)*
- [ ] Table: workspace slug, owner email, sources count, chunks count, monthly queries, created_at
- [ ] Delete button per workspace

### 10.4 — Admin sidebar: add Workspaces link
**File**: `frontend/components/layout/AdminShell.tsx`
- [ ] Add "Workspaces" nav item → `/admin/workspaces`

### 10.5 — Update `IngestForm` for admin: add workspace_id field
**File**: `frontend/components/admin/IngestForm.tsx`
- [x] Add optional "Target Workspace ID" field (for admin-initiated cross-workspace ingest)
- [x] Default to admin's own workspace

### 10.6 — Update threshold tuner to be workspace-aware
**File**: `frontend/components/admin/ThresholdTuner.tsx`
- [x] Add workspace selector dropdown (lists all workspaces)
- [x] PUT `/admin/thresholds` sends `workspace_id` so per-workspace thresholds can be set

**File**: `backend/app/db/models.py`
- [ ] Add `workspace_id` FK to `ThresholdConfigModel` (optional — add in migration 0003 or a follow-up 0004)

---

## GitHub Push Checkpoints

Each checkpoint below is a stable, deployable state. Push and tag before moving to the next phase.

---

### ✅ Checkpoint 1 — Data Model + Migration
**After**: Phase 1 complete (Workspace model + migration + repositories)
**Verify**: `alembic upgrade head` runs clean · `workspaces` table exists · `sources.workspace_id` column exists
**Tag**: `git tag v0.5.0-workspace-model`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 2 — Self-Registration Working
**After**: Phase 2 complete (register endpoint + workspace auto-create + JWT workspace_id claim)
**Verify**: `POST /api/v1/auth/register` → 201 + JWT · JWT contains `workspace_id` claim · duplicate email → 409 · login still works
**Tag**: `git tag v0.5.1-registration`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 3 — Scoped Ingestion Working
**After**: Phase 3 complete (ingest open to all users, workspace-scoped namespace)
**Verify**: Regular user can `POST /api/v1/ingest` · admin blocked from other workspaces without explicit id · Pinecone upsert uses workspace slug as namespace · quota returns 429
**Tag**: `git tag v0.5.2-scoped-ingest`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 4 — Scoped Query Working
**After**: Phase 4 complete (query uses workspace namespace from JWT, not client payload)
**Verify**: Query returns only results from requesting user's namespace · passing `namespace` in payload is ignored · admin can query any workspace by slug
**Tag**: `git tag v0.5.3-scoped-query`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 5 — Quotas + Workspace API
**After**: Phase 5 complete (per-workspace query cap + workspace info endpoint)
**Verify**: `GET /api/v1/workspace/me` returns quota info · query over cap → 429 · `GET /api/v1/workspace/sources` returns correct list
**Tag**: `git tag v0.5.4-quotas`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 6 — Frontend Signup + Sources Dashboard
**After**: Phase 6 complete (signup page + sources dashboard + add source modal)
**Verify**: `/signup` page renders · register flow works end-to-end · `/sources` page lists repos · "Add Source" modal triggers ingest · quota bar reflects real counts
**Tag**: `git tag v0.6.0-frontend-self-serve`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 7 — Full Self-Serve Flow E2E
**After**: Phase 7 complete (query UI workspace-aware, no-sources empty state)
**Verify**: New user: register → connect repo → ask question → get cited answer → submit feedback — full flow works without any admin intervention
**Tag**: `git tag v0.6.1-e2e-self-serve`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 8 — Infra + Seed + Tests Clean
**After**: Phases 8 + 9 complete (Docker env cleaned, seed updated, tests passing)
**Verify**: `docker compose up` boots clean on fresh env · `seed_db.py` creates users + workspaces · all unit tests pass · integration test round-trip passes
**Tag**: `git tag v0.7.0-infra-tests`
**Push**: `git push origin main --tags`

---

### ✅ Checkpoint 9 — Admin Panel Extended
**After**: Phase 10 complete (admin workspace list + per-workspace threshold)
**Verify**: `/admin/workspaces` lists all workspaces · delete workspace cascades · threshold tuner has workspace selector
**Tag**: `git tag v0.8.0-admin-workspaces`
**Push**: `git push origin main --tags`

---

## File Change Summary (Quick Reference)

### Backend — Modified
| File | Change |
|---|---|
| `backend/app/db/models.py` | Add `WorkspaceModel`; add `workspace_id` FK to `SourceModel`, `IngestRunModel`, `ThresholdConfigModel` |
| `backend/app/api/v1/routes/auth_routes.py` | Add `POST /auth/register`; remove `INSECURE-PLAIN` fallback |
| `backend/app/api/v1/routes/ingest_routes.py` | Remove admin-only gate; scope to workspace; add quota check |
| `backend/app/api/v1/routes/query_routes.py` | Remove client namespace override; derive from JWT workspace_id |
| `backend/app/api/v1/routes/admin_routes.py` | Add workspace list + delete endpoints |
| `backend/app/api/v1/router.py` | Include new `workspace_router` |
| `backend/app/core/security.py` | Add `workspace_id` to `AuthenticatedUser` and `issue_jwt_token()` |
| `backend/app/api/v1/dependencies/auth.py` | Extract `workspace_id` from JWT claims |
| `backend/app/domain/services/cost_service.py` | Per-workspace token budget via Redis |
| `backend/app/domain/services/rbac_service.py` | Replace namespace-list RBAC with workspace slug check |
| `backend/app/domain/services/query_service.py` | Add `workspace_id` to `QueryRequest` |
| `backend/app/workers/tasks/ingest_tasks.py` | Set `workspace_id` on `SourceModel` + `IngestRunModel`; use workspace slug as namespace |
| `backend/app/workers/tasks/purge_tasks.py` | Scope purge to `workspace_id` |
| `backend/app/core/config.py` | Remove `default_namespace` field |
| `backend/scripts/seed_db.py` | Use bcrypt; auto-create workspaces for seeded users |

### Backend — New Files
| File | Purpose |
|---|---|
| `backend/app/db/repositories/workspaces_repo.py` | CRUD for `WorkspaceModel` |
| `backend/app/db/repositories/sources_repo.py` | Sources queries by workspace |
| `backend/app/db/migrations/versions/0003_add_workspaces.py` | DB migration |
| `backend/app/api/v1/routes/workspace_routes.py` | `GET /workspace/me`, `GET /workspace/sources`, `DELETE /workspace/sources/{id}` |
| `backend/tests/integration/test_self_serve_flow.py` | E2E integration test |

### Frontend — Modified
| File | Change |
|---|---|
| `frontend/types/user.ts` | Add `workspace_id: string` |
| `frontend/lib/api-client.ts` | Add `postRegister`, `getWorkspaceMe`, `getWorkspaceSources`, `deleteWorkspaceSource`, `postIngest` |
| `frontend/hooks/useQuery.ts` | Remove `namespace` + `index_version` from query payload |
| `frontend/components/layout/Sidebar.tsx` | Add "My Sources" nav; update copy |
| `frontend/components/layout/AdminShell.tsx` | Add "Workspaces" nav link |
| `frontend/components/admin/IngestForm.tsx` | Add workspace_id field |
| `frontend/components/admin/ThresholdTuner.tsx` | Add workspace selector |
| `frontend/app/(auth)/login/page.tsx` | Add link to `/signup` |
| `frontend/app/(query)/page.tsx` | Update hero copy; no-sources CTA; remove internal suggestions |

### Frontend — New Files
| File | Purpose |
|---|---|
| `frontend/app/(auth)/signup/page.tsx` | Self-registration form |
| `frontend/app/(query)/sources/page.tsx` | Sources dashboard page |
| `frontend/components/workspace/AddSourceModal.tsx` | Add GitHub repo modal |
| `frontend/types/workspace.ts` | `WorkspaceInfo`, `Source`, `IngestJob` types |
| `frontend/app/admin/workspaces/page.tsx` | Admin workspace list |

### Infra — Modified
| File | Change |
|---|---|
| `infra/docker/docker-compose.yml` | Remove `DEFAULT_NAMESPACE`; add `REGISTRATION_ENABLED=true` |

### Evaluation — Modified
| File | Change |
|---|---|
| `evaluation/datasets/golden_questions_v1.json` | Replace internal questions; add `workspace_id` field |
| `evaluation/scripts/evaluate_golden_questions.py` | Accept `--workspace-id` arg |
| `backend/scripts/evaluate_golden_questions.py` | Accept `--workspace-id` arg |
