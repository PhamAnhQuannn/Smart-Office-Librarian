"""Pydantic schemas for the authentication API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials submitted to POST /api/v1/auth/token."""

    email: str = Field(description="User account email address.")
    password: str = Field(min_length=1, description="Plaintext password (TLS-only).")


class TokenResponse(BaseModel):
    """JWT returned on successful authentication."""

    access_token: str = Field(description="Signed HS256 JWT.")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(description="Token lifetime in seconds.")


class TokenClaims(BaseModel):
    """Decoded JWT payload exposed to dependants."""

    sub: str = Field(description="User ID (subject).")
    role: str = Field(description="User role (\"user\" or \"admin\").")
    exp: int = Field(description="Unix timestamp expiry.")
