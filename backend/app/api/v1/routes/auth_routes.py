"""Authentication routes — login and self-registration endpoints.

POST /auth/login     accepts {email, password} and returns a signed JWT.
POST /auth/register  creates a new user + workspace and returns a signed JWT.
"""

from __future__ import annotations

import os

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException
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

    if user is None or not user.is_active or not _verify_password(payload.password, user.hashed_password):
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
    )
    return TokenResponse(access_token=token)
