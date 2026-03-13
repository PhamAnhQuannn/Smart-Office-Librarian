"""FR-1 authentication dependency.

Resolves an AuthenticatedUser from an Authorization header value.
Supports Bearer JWT (HS256). Uses JWT_SECRET env var in production;
accepts explicit jwt_secret kwarg for testing.
"""

from __future__ import annotations

import os

from app.core.security import (
    AuthenticatedUser,
    AuthenticationError,
    UserRole,
    decode_jwt_token,
)


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


def _parse_bearer_token(authorization: str) -> str:
    """Extract token string from a 'Bearer <token>' header value."""
    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Authorization header must use 'Bearer' scheme")
    return parts[1]


def get_current_user(
    authorization: str,
    *,
    jwt_secret: str | None = None,
) -> AuthenticatedUser:
    """Resolve an AuthenticatedUser from an Authorization header value.

    jwt_secret: override JWT_SECRET env var (used in tests).
    Raises AuthenticationError (→ HTTP 401) on any authentication failure.
    """
    if not authorization or not authorization.strip():
        raise AuthenticationError("Missing Authorization header")

    secret = jwt_secret if jwt_secret is not None else _get_jwt_secret()
    token = _parse_bearer_token(authorization)
    claims = decode_jwt_token(token, secret=secret)

    user_id: str | None = claims.get("sub")
    if not user_id:
        raise AuthenticationError("JWT missing required 'sub' claim")

    raw_role: str | None = claims.get("role")
    try:
        role = UserRole(raw_role) if raw_role else UserRole.USER
    except ValueError:
        role = UserRole.USER

    return AuthenticatedUser(user_id=user_id, role=role)
