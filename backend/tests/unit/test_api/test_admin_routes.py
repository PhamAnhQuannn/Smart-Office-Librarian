from __future__ import annotations

import base64
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routes.admin_routes import (
    AdminRouteError,
    delete_source_configuration,
    update_role_assignment,
    update_source_configuration,
    update_threshold_configuration,
)
from app.core.logging import (
    AUDIT_LOG_RETENTION_DAYS,
    InMemoryStructuredLogger,
    REDACTED,
    _AUDIT_MAX_CHANGES,
    _AUDIT_MAX_TEXT_LENGTH,
)


def _admin_actor() -> SimpleNamespace:
    return SimpleNamespace(user_id="admin-1", role="admin")


def _make_jwt(payload: dict[str, object], *, secret: str = "step74-jwt-secret") -> str:
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload_b64}.{_b64url(sig)}"


def test_update_source_configuration_rejects_non_admin_actor() -> None:
    logger = InMemoryStructuredLogger()
    non_admin = SimpleNamespace(user_id="user-1", role="user")

    with pytest.raises(AdminRouteError) as exc_info:
        update_source_configuration(
            "source-123",
            {"repo": "octo/repo"},
            actor=non_admin,
            logger=logger,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "FORBIDDEN"


def test_update_source_configuration_emits_sanitized_audit_entry() -> None:
    logger = InMemoryStructuredLogger()
    result = update_source_configuration(
        "source-123",
        {
            "repo": "octo/repo",
            "token": "ghp_sensitive_token_value",
        },
        actor=_admin_actor(),
        logger=logger,
    )

    assert result["audit_retention_days"] == AUDIT_LOG_RETENTION_DAYS
    entry = logger.entries[-1]
    assert entry.event_type == "audit.source.updated"
    assert entry.payload["actor_id"] == "admin-1"
    assert entry.payload["actor_role"] == "admin"
    assert entry.payload["resource_id"] == "source-123"
    assert entry.payload["retention_days"] == AUDIT_LOG_RETENTION_DAYS
    assert entry.payload["changes"]["repo"] == "octo/repo"
    assert entry.payload["changes"]["token"] == REDACTED


def test_update_threshold_configuration_validates_range_and_logs() -> None:
    logger = InMemoryStructuredLogger()

    with pytest.raises(AdminRouteError) as exc_info:
        update_threshold_configuration(
            namespace="prod",
            index_version=1,
            threshold=1.5,
            actor=_admin_actor(),
            logger=logger,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "VALIDATION_ERROR"

    result = update_threshold_configuration(
        namespace="prod",
        index_version=1,
        threshold=0.65,
        actor=_admin_actor(),
        logger=logger,
    )

    assert result["threshold"] == 0.65
    entry = logger.entries[-1]
    assert entry.event_type == "audit.threshold.updated"
    assert entry.payload["resource_id"] == "prod:1"


def test_update_threshold_configuration_uses_actor_from_auth_dependency() -> None:
    token = _make_jwt({"sub": "admin-claims-7", "role": "admin"})
    actor = get_current_user(f"Bearer {token}", jwt_secret="step74-jwt-secret")

    logger = InMemoryStructuredLogger()
    update_threshold_configuration(
        namespace="prod",
        index_version=1,
        threshold=0.71,
        actor=actor,
        logger=logger,
    )

    entry = logger.entries[-1]
    assert entry.event_type == "audit.threshold.updated"
    assert entry.payload["actor_id"] == "admin-claims-7"
    assert entry.payload["actor_role"] == "admin"


def test_update_source_configuration_bounded_audit_structure() -> None:
    logger = InMemoryStructuredLogger()
    oversized_updates = {
        "very_long_value": "x" * (_AUDIT_MAX_TEXT_LENGTH + 50),
        "nested": {
            "items": [str(index) for index in range(25)],
            "token": "ghp_sensitive_token_value",
        },
    }
    oversized_updates.update({f"key_{index}": f"v{index}" for index in range(_AUDIT_MAX_CHANGES + 7)})

    update_source_configuration(
        "source-bounded",
        oversized_updates,
        actor=_admin_actor(),
        logger=logger,
    )

    entry = logger.entries[-1]
    changes = entry.payload["changes"]
    assert len(changes) == _AUDIT_MAX_CHANGES
    assert len(changes["very_long_value"]) == _AUDIT_MAX_TEXT_LENGTH
    assert isinstance(changes["nested"]["items"], list)
    assert len(changes["nested"]["items"]) <= 10


def test_delete_source_configuration_emits_delete_audit_entry() -> None:
    logger = InMemoryStructuredLogger()
    result = delete_source_configuration(
        "source-999",
        actor=_admin_actor(),
        logger=logger,
    )

    assert result["status"] == "queued_for_deletion"
    entry = logger.entries[-1]
    assert entry.event_type == "audit.source.deleted"
    assert entry.payload["changes"]["source_id"] == "source-999"


def test_update_role_assignment_rejects_non_admin_actor() -> None:
    logger = InMemoryStructuredLogger()
    non_admin = SimpleNamespace(user_id="user-1", role="user")

    with pytest.raises(AdminRouteError) as exc_info:
        update_role_assignment(
            "user-2",
            "admin",
            actor=non_admin,
            logger=logger,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "FORBIDDEN"


def test_update_role_assignment_emits_role_audit_entry() -> None:
    logger = InMemoryStructuredLogger()
    result = update_role_assignment(
        "user-42",
        "admin",
        actor=_admin_actor(),
        logger=logger,
    )

    assert result["target_user_id"] == "user-42"
    assert result["new_role"] == "admin"
    assert result["audit_retention_days"] == AUDIT_LOG_RETENTION_DAYS
    entry = logger.entries[-1]
    assert entry.event_type == "audit.role.assigned"
    assert entry.payload["actor_id"] == "admin-1"
    assert entry.payload["resource_id"] == "user-42"
    assert entry.payload["changes"]["new_role"] == "admin"
    assert entry.payload["retention_days"] == AUDIT_LOG_RETENTION_DAYS
