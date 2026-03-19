# Phase 11 — Guest Mode & User History
> **Goal**: Open the product to unauthenticated visitors (guest mode with temporary local history) and give signed-in users persistent, browsable query history built on the existing `QueryLogModel` table.

**Status Legend**: `[ ]` = Not started · `[x]` = Done · `[~]` = In progress

---

## Context: Proposed User Model

Three roles, no paid tier (yet):

| Role | Can query | History | Cross-device | Admin access |
|------|-----------|---------|--------------|-------------|
| **Guest** (unauthenticated) | ✅ yes | Temporary — sessionStorage only, clears on tab close | ❌ | ❌ |
| **Signed-in (free)** | ✅ yes | Persistent — saved to DB via `query_logs` | ✅ | ❌ unless `role = admin` |
| **Admin** | ✅ yes | Persistent | ✅ | ✅ `/admin/*` |

The split is **guest vs signed-in**, not free vs paid.

---

## Gap Analysis — Current vs Target

### What is already aligned ✅

| Area | Evidence |
|------|----------|
| Frontend route separation: `(query)/`, `(auth)/`, `admin/` | Three Next.js route groups already exist with separate layouts |
| Admin separate layout, nav, auth guard | `admin/layout.tsx` → `AdminShell` |
| RBAC (admin vs user) | `UserRole` enum, `user.is_admin` checks in all admin routes |
| Auth system (register + login + JWT) | `POST /api/v1/auth/login` and `/register` working |
| Workspace isolation | `workspace_id` / `workspace_slug` in JWT + Pinecone namespaces |
| History data already collected | `QueryLogModel` has `user_id` (nullable), `query_text`, `sources` JSONB, `created_at`, `confidence` — data is written on every signed-in query already |
| Backend admin route separation | All admin APIs under `/api/v1/admin/*` |
| Token stored in sessionStorage | Already closes with tab — safe baseline for guest UX |

### What is missing ❌

| Gap | Current behaviour | Required behaviour |
|-----|------------------|--------------------|
| **Guest query access** | `AppShell.tsx` redirects unauthenticated visitors to `/login` | Guests can reach `/` and submit queries without logging in |
| **Optional auth on query route** | `query_routes.py` uses `get_authenticated_user` (raises 401 if no token) | Query route uses `get_optional_user` (returns `None` if no token; uses shared guest namespace) |
| **"Sign in to save history" banner** | Not present | Shown on query page when user is not signed in |
| **Guest history (client-side)** | No history stored for guests | Query text + timestamp + response snippet stored in `sessionStorage`; shown in-session only |
| **`GET /api/v1/history`** | Route does not exist | Returns paginated `query_logs` rows for the authenticated user (sorted newest first) |
| **`DELETE /api/v1/history/{log_id}`** | Route does not exist | Deletes a single `query_logs` row owned by the current user |
| **`DELETE /api/v1/history`** | Route does not exist | Clears all `query_logs` rows for the current user |
| **`history/page.tsx` UI** | Stub — "under construction" | Live list of past queries with delete/clear controls |
| **`POST /api/v1/auth/logout`** | Client-side `clearToken()` only | Server endpoint returning 200 (JWT is stateless; blacklisting deferred) |

---

## Route Structure After Phase 11

### Frontend (no URL changes, internal structure only)

```text
frontend/app/
  layout.tsx                     ← root layout (no auth)

  (query)/                       ← public/client routes — no mandatory auth
    layout.tsx                   ← AppShell (soft: shows banner if guest, no redirect)
    page.tsx                     ← query / chat (guests + signed-in)
    history/page.tsx             ← persistent list (signed-in); empty state with CTA (guest)
    sources/page.tsx             ← requires auth (redirect to login if guest)

  (auth)/
    login/page.tsx
    signup/page.tsx

  admin/                         ← unchanged — full auth + admin role required
    layout.tsx → AdminShell
    users/ sources/ ingestion/ thresholds/ analytics/ audit-logs/ workspaces/
```

### Backend (new and modified routes)

```text
POST   /api/v1/auth/login          ← unchanged
POST   /api/v1/auth/register       ← unchanged
POST   /api/v1/auth/logout         ← NEW  (stateless 200; client clears token)

POST   /api/v1/query               ← MODIFIED  (guest access: optional JWT)
POST   /api/v1/feedback            ← unchanged (still needs auth for attribution)

GET    /api/v1/history             ← NEW  (requires auth; returns user's query_logs)
DELETE /api/v1/history/{log_id}   ← NEW  (requires auth; must own the record)
DELETE /api/v1/history            ← NEW  (requires auth; clears all user history)

GET    /api/v1/workspace/me        ← unchanged (requires auth)
GET    /api/v1/workspace/sources   ← unchanged (requires auth)
DELETE /api/v1/workspace/sources/{id}  ← unchanged

POST   /api/v1/ingest              ← unchanged
GET    /api/v1/admin/*             ← unchanged
```

---

## Work Items

### 11.1 — Guest mode: open query route to unauthenticated visitors

**Backend**

**File**: `backend/app/api/v1/dependencies/auth.py`
- [ ] Add `get_optional_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None` — returns `None` (not a 401) when the header is absent or invalid

**File**: `backend/app/api/v1/routes/query_routes.py`
- [ ] Replace `user: Any = Depends(get_authenticated_user)` with `Depends(get_optional_user)`
- [ ] When `user is None` (guest): use a fixed shared namespace `"guest"` (or `"public"`) and skip workspace quota check and query-log user attribution
- [ ] Return 200 normally — guests get answers, just not saved

**Frontend**

**File**: `frontend/components/layout/AppShell.tsx`
- [ ] Remove or soften the mandatory auth redirect inside `AuthenticatedShell` — replace hard redirect with a soft "guest mode" that allows the query page to render
- [ ] Sources page (`/sources`) should still redirect to login (it requires a workspace) — guard at the page level, not the shell level

**File**: `frontend/app/(query)/sources/page.tsx`
- [ ] Move auth guard from shell to page: if `!token`, call `router.replace("/login")`

**File**: `frontend/app/(query)/page.tsx`
- [ ] When `!isLoggedIn`, show a top banner: *"You're browsing as a guest. Sign in to save your history."* with a "Sign in" link to `/login`
- [ ] Add client-side guest history: on each query completion, push `{ query_text, response_snippet, timestamp }` into a `sessionStorage` key `embed_guest_history`

---

### 11.2 — User history: expose QueryLogModel as user-facing history API

> `QueryLogModel` already records every query with `user_id`, `query_text`, `sources`, `created_at`, `confidence`. No new DB table is needed.

**Backend**

**File**: `backend/app/api/v1/routes/history_routes.py` *(new file)*
- [ ] `GET /history` — query `query_logs` WHERE `user_id = user.user_id` ORDER BY `created_at DESC` LIMIT 50 (paginated via `?cursor=` or `?page=`)
  - Response: `{ items: [{ id, query_text, confidence, mode, sources_count, created_at }], total, next_cursor }`
- [ ] `DELETE /history/{log_id}` — delete `QueryLogModel` WHERE `id = log_id AND user_id = user.user_id` → 204; return 404 if not found or not owned by user
- [ ] `DELETE /history` — bulk delete all `query_logs` WHERE `user_id = user.user_id` → 204

**File**: `backend/app/api/v1/router.py`
- [ ] `from app.api.v1.routes.history_routes import router as history_router`
- [ ] `api_router.include_router(history_router)`

**File**: `backend/app/db/repositories/query_logs_repo.py`
- [ ] Add `list_by_user(user_id, *, limit, cursor_created_at) -> list[QueryLogModel]`
- [ ] Add `delete_by_id_and_user(log_id, user_id) -> bool`
- [ ] Add `delete_all_by_user(user_id) -> int` (returns count deleted)

**Frontend**

**File**: `frontend/lib/api-client.ts`
- [ ] Add `HistoryItem` interface: `{ id: string, query_text: string, confidence: string, mode: string, sources_count: number, created_at: string }`
- [ ] Add `getHistory(token: string, cursor?: string): Promise<{ items: HistoryItem[], total: number, next_cursor?: string }>`
- [ ] Add `deleteHistoryItem(id: string, token: string): Promise<void>`
- [ ] Add `clearHistory(token: string): Promise<void>`

**File**: `frontend/app/(query)/history/page.tsx`
- [ ] Replace stub content with:
  - If not logged in: empty state "Sign in to see your query history" + Sign In button
  - If logged in: fetch `getHistory(token)` on mount, render list of items with `query_text`, `confidence`, relative date
  - Per-item delete button → `deleteHistoryItem(id, token)` → removes from state
  - "Clear all history" button with confirmation → `clearHistory(token)` → empty state
  - Loading skeleton while fetching
  - Pagination or "Load more" if `next_cursor` is set

---

### 11.3 — Auth logout endpoint

**File**: `backend/app/api/v1/routes/auth_routes.py`
- [ ] Add `POST /auth/logout` — requires valid JWT (authenticated), returns `204 No Content`
  - No server-side token blacklisting at this stage (JWT is stateless)
  - This allows future middleware to hook into logout events (audit log etc.)

**File**: `frontend/components/layout/AppShell.tsx` (or `Sidebar.tsx`)
- [ ] Logout button currently calls `logout()` → `clearToken()` locally — optionally fire `POST /api/v1/auth/logout` in the background before clearing (non-blocking, fire-and-forget)

---

### 11.4 — Guest session API (deferred)

> Not needed at this stage. Client-side `sessionStorage` guest history is sufficient for the free product. Revisit if/when we need cross-device guest persistence or analytics on guest usage.

- [ ] *(deferred)* `POST /api/v1/guest/session` — create or renew a short-lived guest session token with Redis TTL (30 days)
- [ ] *(deferred)* Server-side guest query log attribution with TTL cleanup

---

## Implementation Priority

| Priority | Item | Effort | Blocking? |
|----------|------|--------|-----------|
| **P0** | 11.1 backend: `get_optional_user` + query route change | S | Guest queries fail without this |
| **P0** | 11.1 frontend: remove hard auth gate from AppShell | S | Guests see login page without this |
| **P1** | 11.1 frontend: guest banner + sessionStorage guest history | S | UX — users won't know how to save |
| **P1** | 11.1 frontend: move auth guard to sources page | S | Sources page must still be protected |
| **P1** | 11.2 backend: `history_routes.py` + repo methods | M | History page remains a stub |
| **P1** | 11.2 frontend: `history/page.tsx` real implementation | M | History page remains a stub |
| **P1** | 11.2 frontend: `api-client.ts` history functions | S | Dependency for history page |
| **P2** | 11.3: `POST /auth/logout` endpoint | XS | Already works client-side |
| **Deferred** | 11.4: guest session API | L | Not needed for free product |

Effort key: XS < 30 min · S = ~1h · M = ~2–4h · L = 1+ day

---

## What Does NOT Change

- Admin routes and layout — fully separate, no guest access, unchanged
- `/api/v1/admin/*` — unchanged
- Workspace isolation (Pinecone namespaces) — unchanged for signed-in users
- Ingest pipeline — unchanged (requires auth, quota-gated)
- RBAC model — unchanged
- Registration / login flow — unchanged
- DB schema — **no new tables needed** (`QueryLogModel.user_id` is already nullable)

---

## Push Checkpoint

After all P0 + P1 items above:

```bash
git add -A
git commit -m "feat: guest query mode, user history API + UI (Phase 11)"
git tag v0.9.0-history
git push origin main --tags
```

Tests to add before tagging:
- `tests/unit/test_history_routes.py` — list/delete/clear history
- `tests/unit/test_optional_auth.py` — query succeeds without JWT (guest), uses guest namespace
- `tests/integration/test_self_serve_flow.py` — extend with `test_guest_can_query` + `test_history_saved_after_login`
