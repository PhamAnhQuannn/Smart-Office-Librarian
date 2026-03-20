"""Authentication routes — login, self-registration, and logout endpoints.

POST /auth/login     accepts {email, password} and returns a signed JWT.
POST /auth/register  creates a new user + workspace and returns a signed JWT.
POST /auth/logout    accepts a valid JWT and returns 204 (client discards the token).
"""

from __future__ import annotations

import os
import secrets as _secrets
from urllib.parse import urlencode as _urlencode

import bcrypt as _bcrypt
import httpx as _httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import _get_jwt_secret
from app.core.security import issue_jwt_token
from app.db.repositories.users_repo import UsersRepository
from app.db.repositories.workspaces_repo import WorkspacesRepository
from app.db.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def _get_workspace_for_user(db: Session, user_id: str) -> tuple[str, str]:
    """Return (workspace_id, workspace_slug) for a user, or ('', '') if none."""
    ws_repo = WorkspacesRepository(db)
    workspace = ws_repo.get_by_owner(user_id)
    if workspace is None:
        return "", ""
    return workspace.id, workspace.slug


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate a user and return a signed JWT access token."""
    repo = UsersRepository(db)
    user = repo.get_by_email(payload.email)

    if (
        user is None
        or not user.is_active
        or not user.hashed_password  # Google-only accounts have no password
        or not _verify_password(payload.password, user.hashed_password)
    ):
        # Return generic 401 without revealing whether the email exists.
        raise HTTPException(status_code=401, detail="Invalid credentials")

    workspace_id, workspace_slug = _get_workspace_for_user(db, user.id)
    secret = _get_jwt_secret()
    token = issue_jwt_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        secret=secret,
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        provider="password",
    )
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Self-register a new user and create their workspace.

    Returns a signed JWT on success (status 201).
    Returns 409 if the email is already registered.
    """
    if os.environ.get("REGISTRATION_ENABLED", "true").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="Self-registration is currently disabled.")
    users_repo = UsersRepository(db)
    if users_repo.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = _hash_password(payload.password)
    user = users_repo.create(
        email=payload.email,
        hashed_password=hashed,
        role="user",
    )

    display_name = payload.display_name.strip() or payload.email.split("@")[0]
    ws_repo = WorkspacesRepository(db)
    workspace = ws_repo.create(owner_id=user.id, display_name=display_name)

    secret = _get_jwt_secret()
    token = issue_jwt_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        secret=secret,
        workspace_id=workspace.id,
        workspace_slug=workspace.slug,
        provider="password",
    )
    return TokenResponse(access_token=token)


# ──────────────────────────────────────────────────────────────────────────────
# Google OAuth 2.0
# ──────────────────────────────────────────────────────────────────────────────

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _get_google_config() -> tuple[str, str, str, str]:
    """Return (client_id, client_secret, redirect_uri, frontend_url) or raise 503."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured on this server")
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    ).strip()
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").strip().rstrip("/")
    return client_id, client_secret, redirect_uri, frontend_url


@router.get("/google")
def google_auth_redirect() -> RedirectResponse:
    """Initiate Google OAuth — redirect the browser to Google's consent screen."""
    client_id, _, redirect_uri, _ = _get_google_config()
    state = _secrets.token_urlsafe(32)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    google_url = f"{_GOOGLE_AUTH_URL}?{_urlencode(params)}"

    resp = RedirectResponse(url=google_url, status_code=302)
    # Store state in a short-lived httponly cookie for CSRF validation in the callback.
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="lax")
    return resp


@router.get("/google/callback")
def google_auth_callback(
    request: Request,
    db: Session = Depends(get_db_session),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle Google's redirect after user consent — exchange code, issue JWT."""
    _, client_secret, redirect_uri, frontend_url = _get_google_config()
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    error_url = f"{frontend_url}/login"

    def _fail(reason: str) -> RedirectResponse:
        resp = RedirectResponse(url=f"{error_url}?error={reason}", status_code=302)
        resp.delete_cookie("oauth_state")
        return resp

    if error:
        return _fail("oauth_denied")

    if not code or not state:
        return _fail("oauth_failed")

    # CSRF: verify state matches the cookie set in /google
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        return _fail("oauth_state_mismatch")

    # Exchange authorization code for an access token
    try:
        token_resp = _httpx.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token: str = token_resp.json()["access_token"]
    except Exception:
        return _fail("oauth_token_exchange_failed")

    # Fetch Google user profile
    try:
        userinfo_resp = _httpx.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
    except Exception:
        return _fail("oauth_userinfo_failed")

    email: str = userinfo.get("email", "").strip().lower()
    if not email:
        return _fail("oauth_no_email")

    display_name: str = userinfo.get("name", "").strip() or email.split("@")[0]

    # Find existing user or auto-create (Google accounts bypass REGISTRATION_ENABLED)
    users_repo = UsersRepository(db)
    user = users_repo.get_by_email(email)
    if user is None:
        user = users_repo.create(email=email, hashed_password=None, role="user")
        ws_repo = WorkspacesRepository(db)
        ws_repo.create(owner_id=user.id, display_name=display_name)

    if not user.is_active:
        return _fail("account_inactive")

    workspace_id, workspace_slug = _get_workspace_for_user(db, user.id)
    secret = _get_jwt_secret()
    token = issue_jwt_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        secret=secret,
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        provider="google",
    )

    # Deliver JWT via URL fragment (fragments are never sent to servers, kept client-side only)
    resp = RedirectResponse(
        url=f"{frontend_url}/auth/google-callback#{token}",
        status_code=302,
    )
    resp.delete_cookie("oauth_state")
    return resp


@router.post("/logout", status_code=204)
def logout(
    db: Session = Depends(get_db_session),  # noqa: ARG001 — kept for future audit-log hook
) -> Response:
    """Invalidate the current session.

    JWTs are stateless — the client must discard the token.
    This endpoint exists as a clean hook for future audit logging or token blocklisting.
    """
    return Response(status_code=204)
