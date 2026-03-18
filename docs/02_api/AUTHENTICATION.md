# Authentication — v1.0

**Last Updated:** 2026-01-01
**Applies to:** Embedlyzer API v1

---

## Overview

Embedlyzer uses stateless **JWT Bearer tokens** for authentication.  
All endpoints except `GET /health`, `GET /ready`, and `GET /metrics` require a valid token.

---

## Login

### `POST /api/v1/auth/token`

Exchange credentials for a short-lived access token.

**Request body:**

```json
{
  "email": "user@example.com",
  "password": "s3cret"
}
```

**Response `200 OK`:**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error codes:**

| Status | Condition |
|--------|-----------|
| `401`  | Invalid credentials |
| `403`  | Account inactive |
| `422`  | Malformed request body |

---

## Token format

Tokens are signed with **HS256** using the `JWT_SECRET` server-side secret.

### Claims

| Claim | Type   | Description |
|-------|--------|-------------|
| `sub` | string | User UUID |
| `role`| string | `"user"` or `"admin"` |
| `exp` | int    | Unix timestamp (UTC) |

---

## Sending the token

Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Token expiry & refresh

Tokens expire after **1 hour** (configurable via `JWT_EXPIRY_SECONDS`).  
There is no refresh endpoint in v1. Clients must re-authenticate with credentials when tokens expire.

---

## Roles

| Role    | Permissions |
|---------|-------------|
| `user`  | Query namespaces they have been granted access to |
| `admin` | Full access to all namespaces, ingestion, analytics, and administration |

Namespace grants are stored in `user_namespace_grants` and applied as Pinecone metadata filters at retrieval time.

---

## Public endpoints (no auth required)

- `GET /health`
- `GET /ready`
- `GET /metrics` (Prometheus scrape endpoint)
