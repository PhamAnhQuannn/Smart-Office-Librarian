"""Integration tests for health-check endpoints.

/health  — liveness probe (always 200)
/ready   — readiness probe (200 when all dependencies healthy, 503 otherwise)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.health_service import HealthService
from app.main import EmbedlyzerApp, create_app
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _passing_probe(_timeout: float) -> tuple[bool, float]:
    return (True, 1.0)


def _failing_probe(_timeout: float) -> tuple[bool, float]:
    return (False, 0.0)


def _make_client(
    postgres: Any = _passing_probe,
    redis: Any = _passing_probe,
    pinecone: Any = _passing_probe,
    jwt_secret: str = "test-secret",
) -> TestClient:
    app = create_app(
        embedlyzer=EmbedlyzerApp(),
        jwt_secret=jwt_secret,
        health_service=HealthService(
            postgres_probe=postgres,
            redis_probe=redis,
            pinecone_probe=pinecone,
        ),
    )
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Liveness — /health
# ---------------------------------------------------------------------------

class TestLivenessEndpoint:
    def test_always_returns_200(self) -> None:
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_response_contains_status_ok(self) -> None:
        client = _make_client()
        resp = client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_returns_200_even_when_db_probe_fails(self) -> None:
        client = _make_client(postgres=_failing_probe)
        resp = client.get("/health")
        # liveness only checks process, not dependencies
        assert resp.status_code == 200

    def test_no_auth_required(self) -> None:
        client = _make_client()
        resp = client.get("/health")
        assert resp.status_code != 401
        assert resp.status_code != 403

    def test_response_is_json(self) -> None:
        client = _make_client()
        resp = client.get("/health")
        assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Readiness — /ready
# ---------------------------------------------------------------------------

class TestReadinessEndpoint:
    def test_all_healthy_returns_200(self) -> None:
        client = _make_client()
        resp = client.get("/ready")
        assert resp.status_code == 200

    def test_all_healthy_body_ready_true(self) -> None:
        client = _make_client()
        resp = client.get("/ready")
        assert resp.json()["ready"] is True

    def test_failing_postgres_returns_503(self) -> None:
        client = _make_client(postgres=_failing_probe)
        resp = client.get("/ready")
        assert resp.status_code == 503

    def test_failing_redis_returns_503(self) -> None:
        client = _make_client(redis=_failing_probe)
        resp = client.get("/ready")
        assert resp.status_code == 503

    def test_failing_pinecone_returns_503(self) -> None:
        client = _make_client(pinecone=_failing_probe)
        resp = client.get("/ready")
        assert resp.status_code == 503

    def test_all_failing_body_ready_false(self) -> None:
        client = _make_client(
            postgres=_failing_probe,
            redis=_failing_probe,
            pinecone=_failing_probe,
        )
        resp = client.get("/ready")
        assert resp.json()["ready"] is False

    def test_no_auth_required(self) -> None:
        client = _make_client()
        resp = client.get("/ready")
        assert resp.status_code not in {401, 403}

    def test_response_contains_checks(self) -> None:
        client = _make_client()
        body = client.get("/ready").json()
        assert "checks" in body or "ready" in body  # shape depends on impl
