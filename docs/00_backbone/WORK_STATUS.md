# WORK_STATUS.md

## 0) Header Metadata
- Project: Smart Office Librarian (Embedlyzer)
- Architecture Version: v1.5
- Status: **Phase 15 complete — citation click-through + workspace rename + sources-aware Ask page**
- Last Updated: 2026-03-20 UTC (session 11)
- Owner: Engineering Team

---

## Session 11 Checkpoint — 2026-03-20 UTC

### Phase 15 — UX polish: citation click-through + workspace rename

**Commit**: `67ef9261`

#### Changes

| Area | File(s) | Change |
|------|---------|--------|
| **Citation click-through** | `frontend/components/query/StreamingAnswer.tsx` | `AnswerText` component splits answer text on `[N]` refs and renders them as teal circular badge buttons; clicking calls `handleCitationClick(n)`: auto-opens citations panel, scrolls `#citation-N` into view, flashes `ring-2 ring-teal-400` highlight for 1.5 s |
| **Citation panel numbered badges** | `frontend/components/query/CitationPanel.tsx` | Each card gets `id="citation-N"` (1-indexed) anchor; teal numbered badge in top-left; `highlighted?: Set<number>` prop drives conditional `ring-2` flash class |
| **Workspace rename** | `frontend/app/(query)/settings/page.tsx` | Workspace name row now has Pencil edit button; clicking enters inline edit mode (input + Check/X buttons); Enter key saves; `PATCH /workspace/me` called via `patchWorkspaceMe()`; success toast on save |
| **PATCH /workspace/me route** | `backend/app/api/v1/routes/workspace_routes.py` | New endpoint — validates `display_name` ≤ 80 chars, calls `WorkspacesRepository.update_display_name()`, logs event |
| **WorkspacesRepository** | `backend/app/db/repositories/workspaces_repo.py` | `update_display_name(workspace, display_name)` method using `flush()` |
| **api-client** | `frontend/lib/api-client.ts` | `patchWorkspaceMe(token, {display_name})` PATCH helper added |

#### All 8 Docker containers healthy on `35.175.156.119` post-deploy.

---

## Session 10 Checkpoint — 2026-03-19 UTC

### Phase 14 — Spec compliance batch 2: UI polish + real data + provider claim

**Commits**: `60b91d0d`, `501c457f`

#### Changes

| Area | File(s) | Change |
|------|---------|--------|
| **Sources page rewrite** | `frontend/app/(query)/sources/page.tsx` | Full rewrite: groups `WorkspaceSource[]` by repo (not file-per-row); "Indexed" status chip; "Added [date]" using `created_at`; expand/collapse per repo to show individual file paths; repo-level delete; light theme matching Sync/Usage |
| **Sync retry button** | `frontend/app/(query)/sync/page.tsx` | Added `RotateCcw` retry button on `status === "failed"` run rows; pre-fills repo URL from `run.repo` and jumps to step 3; `IngestRun` type extended with `repo?` and `branch?` |
| **Usage: remaining queries** | `frontend/app/(query)/usage/page.tsx` | `StatCard` now accepts optional `subtitle` prop; "Queries this month" card shows `X queries remaining this month`; chunks card now reads `workspace.usage.chunks` (real count, not `0`) |
| **Settings: sign-out + provider** | `frontend/app/(query)/settings/page.tsx` | "Sign-in method" row added (Google OAuth / Email & password); "Sign out" button in Account section calls `clearToken()` + `router.replace("/login")` |
| **JWT provider claim** | `backend/app/core/security.py`, `backend/app/api/v1/routes/auth_routes.py` | `issue_jwt_token()` now accepts `provider: str = "password"` claim; login/register routes pass `"password"`, Google OAuth callback passes `"google"` |
| **AuthUser type** | `frontend/types/user.ts` | Added `provider?: "google" \| "password"` field |
| **Chunks count** | `backend/app/db/repositories/chunks_repo.py` | Added `count_by_namespace(namespace)` method using `func.count()` |
| **Workspace /me endpoint** | `backend/app/api/v1/routes/workspace_routes.py` | Returns `usage.chunks` (real count via `ChunksRepository.count_by_namespace`); `usage.queries_this_month` from Redis; new `POST /workspace/ingest` + `GET /workspace/ingest-runs` scoped to authenticated user (fixes critical bug: user pages were calling admin endpoints) |
| **WorkspaceInfo type** | `frontend/lib/api-client.ts` | `usage.chunks: number`; `usage.queries_this_month: number`; `postIngest` now calls `/api/v1/workspace/ingest` (not admin endpoint) |

#### Architecture notes
- Workspace-scoped ingest endpoints (`/workspace/ingest`, `/workspace/ingest-runs`) enforce the rule: user pages must never call admin endpoints.
- The `provider` JWT claim is additive — existing tokens without it default to `undefined` (treated as password in UI) with no breaking change.
- All chunks, query count, and source count in `/workspace/me` are now live data.

#### All 8 Docker containers healthy on `35.175.156.119` post-deploy.

---

## Session 9 Checkpoint — 2026-03-19 UTC

### Phase 13 — Spec compliance batch 1: workspace endpoints + real counters

**Commit**: `99452849` (Sync/Usage/Settings pages, sidebar 6-item nav), `60b91d0d` (workspace-scoped endpoints)

#### Changes

| Area | File(s) | Change |
|------|---------|--------|
| **Sync page** | `frontend/app/(query)/sync/page.tsx` | Calls `WORKSPACE_INGEST_ENDPOINT` + `WORKSPACE_INGEST_RUNS_ENDPOINT`; strategy labels "Fast sync" / "Full refresh" |
| **Usage page** | `frontend/app/(query)/usage/page.tsx` | Real `queries_this_month` from Redis; ID/slug in collapsible section |
| **Workspace endpoints** | `backend/app/api/v1/routes/workspace_routes.py` | `POST /workspace/ingest` + `GET /workspace/ingest-runs`; Redis query counter; `source_url` alias for `repo` |
| **Constants** | `frontend/lib/constants.ts` | `WORKSPACE_INGEST_ENDPOINT`, `WORKSPACE_INGEST_RUNS_ENDPOINT` |

---

## Session 8 Checkpoint — 2026-03-18 UTC

### Google OAuth 2.0 implementation

**Commit**: `v0.9.1-phase13` (Google OAuth)

#### Changes
- `GET /api/v1/auth/google` — redirect to Google consent screen with PKCE-like state cookie (CSRF protection)
- `GET /api/v1/auth/google/callback` — exchange code, fetch userinfo, upsert user, issue JWT → deliver via URL fragment to prevent server logging
- `POST /api/v1/auth/logout` — stateless 204 (frontend clears token)
- Migration `0004_google_oauth` — `hashed_password` nullable (Google-only accounts)
- Frontend: "Sign in with Google" button on login page; `/auth/google-callback` route handler reads fragment token and calls `setToken`
- `hashed_password` nilability guard in login route — Google-only accounts correctly rejected at password endpoint
- DB migration applied on production server; all 8 containers healthy

---

#### Changes

| Area | File | Change |
|------|------|--------|
| **Server-side admin gate** | `frontend/middleware.ts` *(new)* | Next.js Edge middleware checks `embed_session` cookie for `/admin/*` routes before any page renders |
| **Auth cookie** | `frontend/lib/auth.ts` | `setToken` now also writes a `embed_session` cookie `{role, exp}` for middleware; `clearToken` clears it |
| **Analytics endpoint** | `backend/app/api/v1/routes/admin_routes.py` | `GET /api/v1/admin/evaluation/summary?range=7d\|30d\|all` — derived from `query_logs` (confidence, volume, latency, tokens) |
| **Budget endpoint** | `backend/app/api/v1/routes/admin_routes.py` | `GET /api/v1/admin/budget` + `PUT /api/v1/admin/budget/{id}` — per-workspace `monthly_query_cap` with current-month usage |
| **Budget page** | `frontend/app/admin/budget/page.tsx` | Full UI — usage bars, inline cap editor, save per row |
| **API client** | `frontend/lib/api-client.ts` | `BudgetWorkspace`, `adminGetBudget`, `adminUpdateBudget` |

#### Architecture: client vs server separation
- **Client UI** (`(query)/`, `(auth)/`): no mandatory server auth; AppShell is a soft gate
- **Admin UI** (`admin/`): guarded at the **server** level by `middleware.ts`; the `AdminShell` client-side check is a secondary defence
- Admin routes never render on the client unless the server has already validated `role === "admin"` from the signed cookie

#### Test result: 302 passing / 3 pre-existing failures (Caddy TLS ×2, bash syntax ×1)

**Commit**: `v0.9.1-phase12`

---

## Session 6 Checkpoint — 2026-03-18 UTC

### Design analysis: Guest mode + User history (Phase 11)

Reviewed proposed user model (guest → signed-in → admin) and compared against current codebase. Full plan written at [docs/00_backbone/PHASE_11_PLAN.md](docs/00_backbone/PHASE_11_PLAN.md).

**Commits this session**: `4c551c19` (v0.8.1-cleanup — seed_db security fix + query round-trip test)

#### What was confirmed already aligned (no change needed)

| Area | Status |
|------|--------|
| Frontend route groups `(query)/`, `(auth)/`, `admin/` | ✅ Three separate groups with separate layouts |
| Admin separate layout + role-guard | ✅ `AdminShell`, `user.is_admin` checks throughout |
| RBAC (admin vs user) | ✅ `UserRole` enum, enforced on all admin routes |
| JWT auth (register + login) | ✅ Working and tested |
| Workspace isolation (Pinecone namespaces) | ✅ Complete from Phase 1–10 |
| History data collection | ✅ `QueryLogModel` already stores `user_id`, `query_text`, `sources`, `confidence` on every signed-in query |
| Backend `/api/v1/admin/*` separation | ✅ All admin APIs cleanly separated |
| Token in sessionStorage (tab-scoped) | ✅ Correct baseline for guest UX |

#### What is missing — Phase 11 work items

| ID | Item | Priority | File(s) |
|----|------|----------|---------|
| 11.1a | `get_optional_user` dependency (no 401 for guests) | P0 | `dependencies/auth.py` |
| 11.1b | Query route: accept optional user, guest namespace | P0 | `routes/query_routes.py` |
| 11.1c | Remove hard auth gate from `AppShell.tsx` | P0 | `components/layout/AppShell.tsx` |
| 11.1d | Move auth guard to `sources/page.tsx` (page-level) | P1 | `app/(query)/sources/page.tsx` |
| 11.1e | "Sign in to save history" guest banner on query page | P1 | `app/(query)/page.tsx` |
| 11.1f | Client-side guest history in `sessionStorage` | P1 | `app/(query)/page.tsx` |
| 11.2a | `GET/DELETE /api/v1/history` routes | P1 | `routes/history_routes.py` (new) |
| 11.2b | `QueryLogsRepository` list/delete methods | P1 | `db/repositories/query_logs_repo.py` |
| 11.2c | Register history router | P1 | `api/v1/router.py` |
| 11.2d | `getHistory`, `deleteHistoryItem`, `clearHistory` API client functions | P1 | `lib/api-client.ts` |
| 11.2e | `history/page.tsx` real implementation | P1 | `app/(query)/history/page.tsx` |
| 11.3 | `POST /api/v1/auth/logout` endpoint (stateless 204) | P2 | `routes/auth_routes.py` |
| 11.4 | Guest session API (server-side TTL) | Deferred | — |

**No new DB tables needed** — `QueryLogModel.user_id` is already `nullable=True`.

---

## Session 5 Checkpoint — 2026-03-15 UTC

### Completed this session (commit `98036307`, tag `v0.8.0-admin-workspaces`)

| Item | Description | Status |
|------|-------------|--------|
| 8.2 | `REGISTRATION_ENABLED` env flag in `auth_routes.py` + `docker-compose.yml` | ✅ |
| 10.2 | Admin workspace_id override in `ingest_routes.py` | ✅ |
| 10.5 | "Target Workspace ID" field in `IngestForm.tsx` | ✅ |
| 10.6 | Workspace dropdown in `ThresholdTuner.tsx` | ✅ |
| 9.1 | `test_register_short_password_returns_422`, `test_register_disabled_returns_403` added to integration tests | ✅ |
| 9.3 | `test_ingest_quota_exceeded_returns_429` added to integration tests | ✅ |
| Bug | Fixed `ValueError` not JSON-serializable in `sanitize_log_data` for Pydantic v2 validation errors | ✅ |

**Test result**: 429 passing / 5 pre-existing failures (Caddy TLS ×2, bash syntax ×1, postgres connect timeout ×1, ingest flow domain ×1)

**All multitenant migration plan items are now complete.**

---

## DEPLOYMENT MANUAL — What You Need and When

> All code is written and all 417 automated tests pass.
> The steps below are the **only remaining work** before the system serves real traffic.
> They are ordered exactly as you must do them.

---

### STAGE 1 — Before you touch any server (accounts + secrets)

Do this on your laptop, not on any server.

**1.1 — Create third-party accounts and get API keys**

| Service | Where | What to get | Env var to set |
|---|---|---|---|
| **OpenAI** | platform.openai.com → API Keys | Secret key (`sk-…`) | `OPENAI_API_KEY` |
| **Pinecone** | app.pinecone.io → API Keys | API key; create an index (dimension=**1536**, metric=**cosine**) | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` |
| **GitHub** (optional) | github.com → Settings → Developer Settings → Personal Access Tokens | Fine-grained token, scope: `contents:read` on target repos | `GITHUB_TOKEN` |

> Pinecone free tier is enough for MVP. Name your index `embedlyzer-dev` or update `PINECONE_INDEX_NAME`.

**1.2 — Generate your own secrets (run locally, never commit)**

```bash
# JWT signing key
openssl rand -hex 32    # paste result as JWT_SECRET

# Database password (replace default "postgres")
openssl rand -base64 24 # paste result as DB_PASSWORD
```

**1.3 — Fill in your .env file**

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — fill every blank line
```

Mandatory blanks to fill:

| Variable | Source |
|---|---|
| `OPENAI_API_KEY` | Stage 1.1 |
| `PINECONE_API_KEY` | Stage 1.1 |
| `PINECONE_INDEX_NAME` | Stage 1.1 |
| `JWT_SECRET` | Stage 1.2 |
| `DB_PASSWORD` | Stage 1.2 |
| `GITHUB_TOKEN` | Stage 1.1 (only if ingesting private repos) |

---

### STAGE 2 — Start the stack (first-time local or server setup)

```bash
# Start all services (api, worker, postgres, redis, prometheus, grafana, caddy)
docker compose -f infra/docker/docker-compose.yml up -d

# Wait ~15s for postgres to initialize, then run migrations
docker compose exec api alembic upgrade head

# Seed the first admin user
SEED_ADMIN_EMAIL=admin@yourdomain.com \
SEED_ADMIN_PASSWORD=a-strong-password \
docker compose exec api python scripts/seed_db.py

# Verify the API is alive
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

---

### STAGE 3 — Provision cloud server (AWS Lightsail via Terraform)

Skip this stage if you are running on a single self-managed box.

**3.1 — Configure AWS credentials (once)**

```bash
aws configure
# Enter: AWS Access Key ID, Secret Access Key, region (us-east-1), output format (json)
```

**3.2 — Set SSH key in Terraform variables**

Edit `infra/terraform/variables.tf` — set `ssh_public_key` to the contents of your `~/.ssh/id_rsa.pub`.

**3.3 — Apply Terraform**

```bash
cd infra/terraform
terraform init
terraform plan    # review what will be created
terraform apply   # type "yes" to confirm
# Note the static IP printed in the output — you will need it for DNS
```

**3.4 — Point DNS**

In your domain registrar, create an A record:

```
your-domain.com  →  <static IP from terraform output>
```

DNS propagation takes 1–60 minutes.

**3.5 — Enable real TLS in Caddy**

In `infra/caddy/Caddyfile`, replace:

```
tls internal { protocols tls1.3 }
```

with:

```
tls your@email.com
```

Caddy will auto-provision a Let's Encrypt certificate once DNS resolves.

---

### STAGE 4 — Configure GitHub Actions (CI/CD)

**4.1 — Create Environments in the GitHub repo**

Go to: `github.com/<org>/<repo>` → Settings → Environments

| Environment | Required reviewers |
|---|---|
| `staging` | None (auto-deploy on merge to main) |
| `prod` | Add yourself (manual approval required) |

**4.2 — Add GitHub Actions Secrets**

Go to: Settings → Secrets and variables → Actions → New repository secret

| Secret name | Value |
|---|---|
| `STAGING_HOST` | IP or hostname of your staging server |
| `PROD_HOST` | IP or hostname of your production server |
| `STAGING_SSH_KEY` | Contents of the private key matching the staging server's `authorized_keys` |
| `PROD_SSH_KEY` | Contents of the private key for the production server |

Once these are set, pushing to `main` and triggering `deploy.yml` with environment=staging will SSH into the server and run `infra/scripts/deploy.sh` automatically.

---

### STAGE 5 — Post-deployment smoke checks

Run these after every first deploy or upgrade:

```bash
# 1 — API liveness
curl https://your-domain.com/health
# Expected: {"status": "ok"}

# 2 — API readiness (all dependencies healthy)
curl https://your-domain.com/ready
# Expected: {"db": true, "redis": true, "pinecone": true}

# 3 — Migrations are at head
docker compose exec api alembic current
# Expected: prints latest revision hash + (head)

# 4 — Celery worker is running
docker compose logs worker | grep "ready"
# Expected: "celery@<hostname> ready."

# 5 — Grafana dashboards load
# Open: https://your-domain.com:3001
# Expected: 4 dashboards visible
# Default credentials: admin / admin  <-- change in infra/grafana/grafana.ini

# 6 — Ingest a test document
curl -X POST https://your-domain.com/api/v1/ingest \
  -H "Authorization: Bearer <your-jwt>" \
  -d '{"source_url": "https://github.com/your-org/your-repo"}'

# 7 — Run a test query
curl -X POST https://your-domain.com/api/v1/query \
  -H "Authorization: Bearer <your-jwt>" \
  -d '{"query_text": "What is this repo about?", "stream": false}'

# 8 — Run golden-question evaluation
docker compose exec api python scripts/evaluate_golden_questions.py
# Expected: >= 80% pass rate
```

---

### STAGE 6 — Remaining open items (non-blocking for MVP)

| ID | What | Action needed |
|---|---|---|
| C-03 | `frontend/public/favicon.ico` is a 0-byte placeholder | Replace with a real `.ico` file before going public |
| C-05 | No email alerts for budget/threshold breaches | Wire SMTP or integrate an alerting service (future feature) |

---

## Previous Step Tracking

- Last completed step: Step 75 — Regression gate + commit for the Step 74 slice
- Branch: main
- Commit: 0e4a0a6c85d47e5f04ef31a76b88b21e13f33547
- Test suite: **417 passing, 1 pre-existing Windows bash failure** (not a code defect)
- Known Issues / Blockers: None — code is complete.