"""FR-1 integration tests: auth + RBAC filter wiring.

Tests the full flow from Authorization header → AuthenticatedUser →
build_rbac_filter → dict compatible with QueryService.execute(rbac_filter=...).

Aligned to TESTING.md §11 integration contracts:
- Permission-filtered retrieval (FR-1.3)
- 401/403 boundary contracts (UNAUTHENTICATED)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.v1.dependencies.auth import get_current_user
from app.core.security import (
    AuthenticatedUser,
    AuthenticationError,
    UserRole,
    build_rbac_filter,
    encrypt_secret_value,
)

_SECRET = "integration-test-jwt-secret"


def _make_jwt(payload: dict, *, secret: str = _SECRET) -> str:
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload_b64}.{_b64url(sig)}"


def test_auth_flow_admin_resolves_with_correct_role_and_rbac_filter() -> None:
    """Admin user resolves with ADMIN role and valid RBAC filter containing their user_id."""
    token = _make_jwt({"sub": "admin-1", "role": "admin", "exp": int(time.time()) + 600})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)

    assert user.user_id == "admin-1"
    assert user.role == UserRole.ADMIN

    rbac_filter = build_rbac_filter(user)
    user_clause = next(c for c in rbac_filter["$or"] if "allowed_user_ids" in c)
    assert "admin-1" in user_clause["allowed_user_ids"]["$in"]


def test_auth_flow_regular_user_resolves_with_public_and_private_rbac_clauses() -> None:
    """Regular user gets USER role; RBAC filter has both public visibility and allowed_user_ids clauses."""
    token = _make_jwt({"sub": "user-123", "role": "user", "exp": int(time.time()) + 600})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)

    assert user.role == UserRole.USER

    rbac_filter = build_rbac_filter(user)
    public_clause = next(c for c in rbac_filter["$or"] if "visibility" in c)
    user_clause = next(c for c in rbac_filter["$or"] if "allowed_user_ids" in c)

    assert public_clause["visibility"]["$eq"] == "public"
    assert user_clause["allowed_user_ids"]["$in"] == ["user-123"]


def test_auth_flow_rbac_filter_is_dict_compatible_with_query_service() -> None:
    """RBAC filter structure is a dict with '$or' list — compatible with QueryRequest.rbac_filter."""
    token = _make_jwt({"sub": "qa-user-7", "role": "user"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)
    rbac_filter = build_rbac_filter(user)

    assert isinstance(rbac_filter, dict)
    assert "$or" in rbac_filter
    assert isinstance(rbac_filter["$or"], list)


def test_auth_flow_unauthenticated_request_raises_authentication_error() -> None:
    """Missing authorization raises AuthenticationError (→ 401 UNAUTHENTICATED)."""
    with pytest.raises(AuthenticationError):
        get_current_user("", jwt_secret=_SECRET)


def test_auth_flow_expired_token_raises_authentication_error() -> None:
    """Expired JWT raises AuthenticationError (→ 401); no user is resolved."""
    token = _make_jwt({"sub": "user-1", "exp": int(time.time()) - 10})
    with pytest.raises(AuthenticationError, match="expired"):
        get_current_user(f"Bearer {token}", jwt_secret=_SECRET)


def test_auth_flow_tampered_token_raises_authentication_error() -> None:
    """Token signed with a different secret raises AuthenticationError (→ 401)."""
    token = _make_jwt({"sub": "user-1"}, secret="attacker-secret")
    with pytest.raises(AuthenticationError):
        get_current_user(f"Bearer {token}", jwt_secret=_SECRET)


def test_auth_flow_supports_encrypted_runtime_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auth flow can resolve JWT secret from encrypted environment variable."""
    token = _make_jwt({"sub": "enc-user", "role": "user"}, secret="runtime-secret")
    encrypted_secret = encrypt_secret_value("runtime-secret", key_material="runtime-master-key")

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTED", encrypted_secret)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTION_KEY", "runtime-master-key")

    user = get_current_user(f"Bearer {token}")
    assert user.user_id == "enc-user"
    assert user.role == UserRole.USER


def test_auth_flow_workspace_claims_propagated_to_authenticated_user() -> None:
    """workspace_id and workspace_slug claims from the JWT are available on AuthenticatedUser."""
    token = _make_jwt({
        "sub": "ws-user-1",
        "role": "user",
        "workspace_id": "ws-abc-xyz-123",
        "workspace_slug": "ws-acmecorp",
        "exp": int(time.time()) + 600,
    })
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)

    assert user.user_id == "ws-user-1"
    assert user.workspace_id == "ws-abc-xyz-123"
    assert user.workspace_slug == "ws-acmecorp"


def test_auth_flow_workspace_claims_default_to_empty_string_when_absent() -> None:
    """Legacy JWTs without workspace claims still resolve without error."""
    token = _make_jwt({"sub": "legacy-user", "role": "user"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)

    assert user.workspace_id == ""
    assert user.workspace_slug == ""
