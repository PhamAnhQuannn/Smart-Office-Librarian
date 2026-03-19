"""Tests for the get_optional_user dependency (guest mode auth).

Verifies that:
- A valid JWT returns an AuthenticatedUser
- A missing/empty authorization string returns None (not raises)
- An expired token returns None (not raises)
- An invalid signature returns None (not raises)
- A malformed header returns None (not raises)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.v1.dependencies.auth import get_optional_user
from app.core.security import AuthenticatedUser, UserRole

_SECRET = "optional-auth-test-secret"


def _make_jwt(payload: dict, *, secret: str = _SECRET) -> str:
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload_b64}.{_b64url(sig)}"


def test_valid_jwt_returns_authenticated_user() -> None:
    token = _make_jwt(
        {
            "sub": "user-abc",
            "role": "user",
            "workspace_id": "ws-1",
            "workspace_slug": "ws-slug-1",
            "exp": int(time.time()) + 3600,
        }
    )
    result = get_optional_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert isinstance(result, AuthenticatedUser)
    assert result.user_id == "user-abc"
    assert result.role == UserRole.USER
    assert result.workspace_id == "ws-1"


def test_empty_authorization_returns_none() -> None:
    assert get_optional_user("", jwt_secret=_SECRET) is None


def test_none_like_empty_string_returns_none() -> None:
    assert get_optional_user("   ", jwt_secret=_SECRET) is None


def test_expired_token_returns_none() -> None:
    token = _make_jwt({"sub": "user-1", "exp": int(time.time()) - 60})
    result = get_optional_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert result is None


def test_invalid_signature_returns_none() -> None:
    token = _make_jwt({"sub": "user-1", "exp": int(time.time()) + 3600})
    result = get_optional_user(f"Bearer {token}", jwt_secret="wrong-secret")
    assert result is None


def test_malformed_header_not_bearer_returns_none() -> None:
    token = _make_jwt({"sub": "user-1", "exp": int(time.time()) + 3600})
    result = get_optional_user(f"Token {token}", jwt_secret=_SECRET)
    assert result is None


def test_garbage_token_returns_none() -> None:
    result = get_optional_user("Bearer not.a.real.jwt", jwt_secret=_SECRET)
    assert result is None


def test_admin_role_is_preserved() -> None:
    token = _make_jwt(
        {"sub": "admin-1", "role": "admin", "workspace_id": "ws-admin", "exp": int(time.time()) + 3600}
    )
    result = get_optional_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert result is not None
    assert result.role == UserRole.ADMIN
