"""FR-1 unit tests: auth dependency and security primitives.

Aligned to TESTING.md §9.1 AuthDependency Tests:
- Valid JWT extracts claims
- Expired/invalid/missing token returns 401
- user not found returns 401
- Role extraction (admin/user/default)
- RBAC filter structure (DECISIONS.md §5.1)
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

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.v1.dependencies.auth import get_current_user
from app.core.security import (
    AuthenticatedUser,
    AuthenticationError,
    UserRole,
    build_rbac_filter,
    decode_jwt_token,
    encrypt_secret_value,
)

_SECRET = "unit-test-jwt-secret-key"


def _make_jwt(payload: dict, *, secret: str = _SECRET) -> str:
    """Build a minimal HS256 JWT for testing."""

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload_b64}.{_b64url(sig)}"


# ---------------------------------------------------------------------------
# decode_jwt_token
# ---------------------------------------------------------------------------


def test_decode_jwt_extracts_all_claims_for_valid_token() -> None:
    token = _make_jwt({"sub": "user-1", "role": "admin", "exp": int(time.time()) + 600})
    claims = decode_jwt_token(token, secret=_SECRET)
    assert claims["sub"] == "user-1"
    assert claims["role"] == "admin"


def test_decode_jwt_accepts_token_without_expiry() -> None:
    token = _make_jwt({"sub": "user-2"})
    claims = decode_jwt_token(token, secret=_SECRET)
    assert claims["sub"] == "user-2"


def test_decode_jwt_raises_on_invalid_signature() -> None:
    token = _make_jwt({"sub": "user-1"}, secret=_SECRET)
    with pytest.raises(AuthenticationError):
        decode_jwt_token(token, secret="wrong-secret")


def test_decode_jwt_raises_on_expired_token() -> None:
    token = _make_jwt({"sub": "user-1", "exp": int(time.time()) - 1})
    with pytest.raises(AuthenticationError, match="expired"):
        decode_jwt_token(token, secret=_SECRET)


def test_decode_jwt_raises_on_malformed_two_part_token() -> None:
    with pytest.raises(AuthenticationError):
        decode_jwt_token("header.payload", secret=_SECRET)


def test_decode_jwt_raises_on_single_segment_token() -> None:
    with pytest.raises(AuthenticationError):
        decode_jwt_token("notavalidjwttoken", secret=_SECRET)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


def test_get_current_user_extracts_user_id_and_admin_role() -> None:
    token = _make_jwt({"sub": "admin-42", "role": "admin"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert user.user_id == "admin-42"
    assert user.role == UserRole.ADMIN
    assert user.is_admin is True


def test_get_current_user_extracts_user_role() -> None:
    token = _make_jwt({"sub": "user-99", "role": "user"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert user.role == UserRole.USER
    assert user.is_admin is False


def test_get_current_user_defaults_to_user_role_when_role_claim_absent() -> None:
    token = _make_jwt({"sub": "user-7"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert user.role == UserRole.USER


def test_get_current_user_defaults_to_user_role_for_unrecognized_role_value() -> None:
    token = _make_jwt({"sub": "user-1", "role": "superuser"})
    user = get_current_user(f"Bearer {token}", jwt_secret=_SECRET)
    assert user.role == UserRole.USER


def test_get_current_user_raises_on_empty_authorization_header() -> None:
    with pytest.raises(AuthenticationError):
        get_current_user("", jwt_secret=_SECRET)


def test_get_current_user_raises_on_unsupported_auth_scheme() -> None:
    token = _make_jwt({"sub": "user-1"})
    with pytest.raises(AuthenticationError):
        get_current_user(f"ApiKey {token}", jwt_secret=_SECRET)


def test_get_current_user_raises_on_invalid_jwt() -> None:
    with pytest.raises(AuthenticationError):
        get_current_user("Bearer not-a-real-token", jwt_secret=_SECRET)


def test_get_current_user_raises_when_sub_claim_missing() -> None:
    token = _make_jwt({"role": "user"})  # no 'sub'
    with pytest.raises(AuthenticationError, match="sub"):
        get_current_user(f"Bearer {token}", jwt_secret=_SECRET)


def test_get_current_user_supports_encrypted_env_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _make_jwt({"sub": "encrypted-user", "role": "user"}, secret="runtime-jwt-secret")
    encrypted_secret = encrypt_secret_value("runtime-jwt-secret", key_material="master-key-material")

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTED", encrypted_secret)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTION_KEY", "master-key-material")

    user = get_current_user(f"Bearer {token}")
    assert user.user_id == "encrypted-user"
    assert user.role == UserRole.USER


def test_get_current_user_raises_when_encrypted_secret_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _make_jwt({"sub": "encrypted-user"}, secret="runtime-jwt-secret")
    encrypted_secret = encrypt_secret_value("runtime-jwt-secret", key_material="master-key-material")

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTED", encrypted_secret)
    monkeypatch.delenv("JWT_SECRET_ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_ENCRYPTION_KEY"):
        get_current_user(f"Bearer {token}")


def test_get_current_user_raises_when_encrypted_secret_cannot_decrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    token = _make_jwt({"sub": "encrypted-user"}, secret="runtime-jwt-secret")
    encrypted_secret = encrypt_secret_value("runtime-jwt-secret", key_material="master-key-material")

    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTED", encrypted_secret)
    monkeypatch.setenv("JWT_SECRET_ENCRYPTION_KEY", "wrong-master-key")

    with pytest.raises(RuntimeError, match="could not be decrypted"):
        get_current_user(f"Bearer {token}")


# ---------------------------------------------------------------------------
# build_rbac_filter
# ---------------------------------------------------------------------------


def test_build_rbac_filter_returns_or_structure() -> None:
    user = AuthenticatedUser(user_id="user-5", role=UserRole.USER)
    rbac_filter = build_rbac_filter(user)
    assert "$or" in rbac_filter
    assert len(rbac_filter["$or"]) == 2


def test_build_rbac_filter_includes_public_visibility_clause() -> None:
    user = AuthenticatedUser(user_id="user-5", role=UserRole.USER)
    rbac_filter = build_rbac_filter(user)
    public_clause = next(
        (c for c in rbac_filter["$or"] if c.get("visibility", {}).get("$eq") == "public"),
        None,
    )
    assert public_clause is not None


def test_build_rbac_filter_includes_correct_user_id_in_allowed_list() -> None:
    user = AuthenticatedUser(user_id="alice-123", role=UserRole.USER)
    rbac_filter = build_rbac_filter(user)
    user_clause = next(c for c in rbac_filter["$or"] if "allowed_user_ids" in c)
    assert user_clause["allowed_user_ids"]["$in"] == ["alice-123"]
