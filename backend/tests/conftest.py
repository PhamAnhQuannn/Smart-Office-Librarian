"""Shared pytest fixtures for the Embedlyzer backend test suite."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.core.logging import InMemoryStructuredLogger
from app.core.metrics import InMemoryMetricsRegistry
from app.core.security import AuthenticatedUser, UserRole
from app.db.repositories.feedback_repo import InMemoryFeedbackRepository
from app.db.repositories.query_logs_repo import InMemoryQueryLogsRepository
from app.domain.services.cost_service import CostService
from app.domain.services.feedback_service import FeedbackService
from app.domain.services.health_service import HealthService
from app.domain.services.threshold_service import ThresholdService
from app.main import EmbedlyzerApp, create_app

# ── Constants ──────────────────────────────────────────────────────────────────

TEST_JWT_SECRET = "test-secret-do-not-use-in-production"


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(
    *,
    user_id: str = "user-1",
    role: str = "user",
    workspace_id: str = "ws-test-001",
    workspace_slug: str = "ws-testuser001",
    exp: int | None = None,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Build a signed HS256 JWT for tests."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "workspace_id": workspace_id,
        "workspace_slug": workspace_slug,
        "exp": int(time.time()) + 3600 if exp is None else exp,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


# ── Auth fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture()
def jwt_secret() -> str:
    return TEST_JWT_SECRET


@pytest.fixture()
def user_token(jwt_secret: str) -> str:
    return make_jwt(user_id="test-user", role="user", secret=jwt_secret)


@pytest.fixture()
def admin_token(jwt_secret: str) -> str:
    return make_jwt(user_id="test-admin", role="admin", secret=jwt_secret)


@pytest.fixture()
def user_auth_headers(user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture()
def admin_auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="test-user",
        role=UserRole.USER,
        workspace_id="ws-test-001",
        workspace_slug="ws-testuser001",
    )


@pytest.fixture()
def admin_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="test-admin",
        role=UserRole.ADMIN,
        workspace_id="ws-admin-001",
        workspace_slug="ws-adminuser001",
    )


# ── App / HTTP client fixtures ─────────────────────────────────────────────────

@pytest.fixture()
def embedlyzer_app() -> EmbedlyzerApp:
    return EmbedlyzerApp()


@pytest.fixture()
def test_app(embedlyzer_app: EmbedlyzerApp, jwt_secret: str):
    """FastAPI test application with test JWT secret."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    app = create_app(embedlyzer=embedlyzer_app, jwt_secret=jwt_secret)
    return TestClient(app)


# ── Repository fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def query_logs_repo() -> InMemoryQueryLogsRepository:
    return InMemoryQueryLogsRepository()


@pytest.fixture()
def feedback_repo() -> InMemoryFeedbackRepository:
    return InMemoryFeedbackRepository()


# ── Service fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def logger() -> InMemoryStructuredLogger:
    return InMemoryStructuredLogger()


@pytest.fixture()
def metrics() -> InMemoryMetricsRegistry:
    return InMemoryMetricsRegistry()


@pytest.fixture()
def threshold_service() -> ThresholdService:
    return ThresholdService()


@pytest.fixture()
def cost_service() -> CostService:
    return CostService(monthly_token_budget=1_000_000)


@pytest.fixture()
def feedback_service(feedback_repo: InMemoryFeedbackRepository) -> FeedbackService:
    return FeedbackService(feedback_repo=feedback_repo)


@pytest.fixture()
def health_service() -> HealthService:
    """HealthService with always-passing probes for unit tests."""
    return HealthService(
        postgres_probe=lambda _: (True, 1.0),
        redis_probe=lambda _: (True, 1.0),
        pinecone_probe=lambda _: (True, 1.0),
    )
