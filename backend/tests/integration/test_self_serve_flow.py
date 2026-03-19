"""Self-serve flow integration test.

Exercises the full tenant lifecycle via the HTTP layer using an in-memory
SQLite database in place of PostgreSQL:

  register → login → workspace/me → ingest (queued) → list sources → delete source

Only the tables actually used by these routes are created (users, workspaces,
sources), which avoids SQLite incompatibility with the postgresql.JSONB type
used by the query_logs table.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import SourceModel, UserModel, WorkspaceModel  # noqa: F401 – register models
from app.db.session import get_db_session
from app.main import EmbedlyzerApp, create_app

# ── Constants ─────────────────────────────────────────────────────────────────

JWT_SECRET = "self-serve-integration-test-secret"
TEST_EMAIL = "alice@example.com"
TEST_PASS = "correct-horse-battery-staple"
TEST_DISPLAY = "Alice"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _set_jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject JWT_SECRET into the env so auth_routes._get_jwt_secret() works."""
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)


@pytest.fixture()
def client() -> TestClient:
    """Return a TestClient backed by an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create only the tables used by this flow (avoids postgresql.JSONB issue).
    for table in (
        UserModel.__table__,
        WorkspaceModel.__table__,
        SourceModel.__table__,
    ):
        table.create(bind=engine, checkfirst=True)

    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _override_db() -> Generator[Session, None, None]:
        s = TestingSession()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app = create_app(embedlyzer=EmbedlyzerApp(), jwt_secret=JWT_SECRET)
    app.dependency_overrides[get_db_session] = _override_db
    return TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _register(client: TestClient) -> str:
    """Register a fresh user and return the bearer token."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASS, "display_name": TEST_DISPLAY},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["access_token"]


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_register_returns_jwt(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASS, "display_name": TEST_DISPLAY},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_duplicate_register_returns_409(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
    )
    assert resp.status_code == 409


def test_login_after_register_returns_jwt(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_workspace_me_returns_slug_and_zero_usage(client: TestClient) -> None:
    token = _register(client)
    resp = client.get("/api/v1/workspace/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "slug" in body
    assert body["usage"]["sources"] == 0


def test_ingest_queues_job(client: TestClient) -> None:
    token = _register(client)
    resp = client.post(
        "/api/v1/ingest",
        json={"repo": "octocat/hello-world", "branch": "main"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["repo"] == "octocat/hello-world"
    assert "job_id" in body


def test_sources_list_is_empty_before_worker_runs(client: TestClient) -> None:
    token = _register(client)
    resp = client.get(
        "/api/v1/workspace/sources",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"] == []
    assert body["total"] == 0


def test_delete_nonexistent_source_returns_404(client: TestClient) -> None:
    token = _register(client)
    resp = client.delete(
        "/api/v1/workspace/sources/nonexistent-source-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_full_self_serve_flow(client: TestClient) -> None:
    """End-to-end: register → login → workspace → ingest → sources → not-found delete."""
    # Step 1: register
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASS, "display_name": TEST_DISPLAY},
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Step 2: login with same credentials
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASS},
    )
    assert login_resp.status_code == 200

    # Step 3: workspace info
    me_resp = client.get("/api/v1/workspace/me", headers=auth)
    assert me_resp.status_code == 200
    ws = me_resp.json()
    assert ws["usage"]["sources"] == 0
    assert ws["limits"]["max_sources"] > 0

    # Step 4: trigger ingest (job is queued; worker not running in tests)
    ingest_resp = client.post(
        "/api/v1/ingest",
        json={"repo": "test-org/test-repo"},
        headers=auth,
    )
    assert ingest_resp.status_code == 202
    assert ingest_resp.json()["status"] == "queued"

    # Step 5: sources list is still empty (worker hasn't run)
    sources_resp = client.get("/api/v1/workspace/sources", headers=auth)
    assert sources_resp.status_code == 200
    assert sources_resp.json()["sources"] == []

    # Step 6: unauthenticated access is blocked
    unauth_resp = client.get("/api/v1/workspace/me")
    assert unauth_resp.status_code == 401


# ---------------------------------------------------------------------------
# 9.1 — Additional register validation tests
# ---------------------------------------------------------------------------


def test_register_short_password_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "short"},
    )
    # The app normalises validation errors to 400 via the RequestValidationError handler.
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "VALIDATION_ERROR"


def test_register_disabled_returns_403(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REGISTRATION_ENABLED", "false")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "blocked@example.com", "password": "goodpassword123"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 9.3 — Ingest quota enforcement
# ---------------------------------------------------------------------------


@pytest.fixture()
def quota_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, sessionmaker]:
    """TestClient with an exposed session factory so tests can mutate DB state."""
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (UserModel.__table__, WorkspaceModel.__table__, SourceModel.__table__):
        table.create(bind=engine, checkfirst=True)

    TestingSessionFactory: sessionmaker = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )

    def _override_db() -> Generator[Session, None, None]:
        s = TestingSessionFactory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app = create_app(embedlyzer=EmbedlyzerApp(), jwt_secret=JWT_SECRET)
    app.dependency_overrides[get_db_session] = _override_db
    return TestClient(app), TestingSessionFactory


def test_ingest_quota_exceeded_returns_429(
    quota_client: tuple[TestClient, sessionmaker],
) -> None:
    http, SessionFactory = quota_client

    resp = http.post(
        "/api/v1/auth/register",
        json={"email": "quota@example.com", "password": TEST_PASS},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    # Force max_sources to 0 so the next ingest hits the quota ceiling.
    db = SessionFactory()
    try:
        ws = db.query(WorkspaceModel).first()
        assert ws is not None
        ws.max_sources = 0
        db.commit()
    finally:
        db.close()

    resp = http.post(
        "/api/v1/ingest",
        json={"repo": "octocat/hello-world"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 429
    assert resp.json()["error_code"] == "QUOTA_EXCEEDED"
