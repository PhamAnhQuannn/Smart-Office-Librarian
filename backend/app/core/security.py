"""FR-1 core security primitives.

Provides HS256 JWT verification, user role extraction, and RBAC filter
construction per DECISIONS.md §4-5 and REQUIREMENTS.md FR-1.1/FR-1.2/FR-1.3.
No external dependencies; pure stdlib only.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


class AuthenticationError(Exception):
    """Raised on authentication failure (→ HTTP 401 UNAUTHENTICATED)."""

    error_code: str = "UNAUTHENTICATED"


def _b64url_decode(data: str) -> bytes:
    padding = (4 - len(data) % 4) % 4
    return base64.urlsafe_b64decode(data + "=" * padding)


def decode_jwt_token(token: str, *, secret: str) -> dict[str, Any]:
    """Verify an HS256 JWT and return its payload claims.

    Raises AuthenticationError on invalid signature, expiry, or malformed input.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed JWT: expected 3 dot-separated parts")

        header_b64, payload_b64, signature_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(
            secret.encode(),
            signing_input,
            hashlib.sha256,
        ).digest()
        received_sig = _b64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, received_sig):
            raise AuthenticationError("JWT signature verification failed")

        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode())

        exp = payload.get("exp")
        if exp is not None and exp < time.time():
            raise AuthenticationError("JWT has expired")

        return payload

    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError(f"JWT decode error: {exc}") from exc


def build_rbac_filter(user: AuthenticatedUser) -> dict[str, Any]:
    """Return the canonical Pinecone RBAC metadata filter (DECISIONS.md §5.1).

    Semantics: (visibility == \"public\") OR (allowed_user_ids $in [user_id])
    """
    return {
        "$or": [
            {"visibility": {"$eq": "public"}},
            {"allowed_user_ids": {"$in": [user.user_id]}},
        ]
    }
