from __future__ import annotations

import base64
import hashlib
import hmac
import json
from types import SimpleNamespace

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routes.admin_routes import (
    update_role_assignment,
    update_source_configuration,
    update_threshold_configuration,
)
from app.core.logging import (
    AUDIT_LOG_RETENTION_DAYS,
    InMemoryStructuredLogger,
    _AUDIT_MAX_CHANGES,
    _AUDIT_MAX_TEXT_LENGTH,
)


def _make_jwt(payload: dict[str, object], *, secret: str = "step74-int-jwt") -> str:
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_b64 = _b64url(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload_b64}.{_b64url(sig)}"


def test_admin_source_and_threshold_changes_append_audit_entries() -> None:
    logger = InMemoryStructuredLogger()
    token = _make_jwt({"sub": "admin-1", "role": "admin"})
    actor = get_current_user(f"Bearer {token}", jwt_secret="step74-int-jwt")

    update_source_configuration(
        "source-123",
        {"repo": "octo/repo", "visibility": "private"},
        actor=actor,
        logger=logger,
    )
    first_entry = logger.entries[0]

    update_threshold_configuration(
        namespace="prod",
        index_version=1,
        threshold=0.7,
        actor=actor,
        logger=logger,
    )

    entries = logger.entries
    assert len(entries) == 2
    assert entries[0] == first_entry
    assert entries[0].event_type == "audit.source.updated"
    assert entries[1].event_type == "audit.threshold.updated"
    assert entries[0].payload["actor_id"] == "admin-1"
    assert entries[1].payload["actor_id"] == "admin-1"
    assert entries[0].payload["actor_role"] == "admin"
    assert entries[1].payload["actor_role"] == "admin"


def test_admin_audit_entries_include_minimum_retention_policy() -> None:
    logger = InMemoryStructuredLogger()
    actor = SimpleNamespace(user_id="admin-1", role="admin")

    update_source_configuration(
        "source-123",
        {"repo": "octo/repo"},
        actor=actor,
        logger=logger,
    )
    update_threshold_configuration(
        namespace="prod",
        index_version=1,
        threshold=0.65,
        actor=actor,
        logger=logger,
    )

    for entry in logger.entries:
        assert entry.payload["retention_days"] >= AUDIT_LOG_RETENTION_DAYS


def test_role_change_writes_audit_row() -> None:
    """TESTING 11.9: role change writes audit row."""
    logger = InMemoryStructuredLogger()
    actor = SimpleNamespace(user_id="admin-1", role="admin")

    result = update_role_assignment(
        "user-55",
        "admin",
        actor=actor,
        logger=logger,
    )

    assert result["target_user_id"] == "user-55"
    assert result["new_role"] == "admin"

    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.event_type == "audit.role.assigned"
    assert entry.payload["actor_id"] == "admin-1"
    assert entry.payload["resource_id"] == "user-55"
    assert entry.payload["changes"]["new_role"] == "admin"
    assert entry.payload["retention_days"] >= AUDIT_LOG_RETENTION_DAYS


def test_audit_changes_payload_is_bounded() -> None:
    logger = InMemoryStructuredLogger()
    actor = SimpleNamespace(user_id="admin-1", role="admin")

    updates = {
        "long_value": "y" * (_AUDIT_MAX_TEXT_LENGTH + 100),
        "nested": {"items": [str(index) for index in range(50)]},
    }
    updates.update({f"field_{index}": index for index in range(_AUDIT_MAX_CHANGES + 10)})

    update_source_configuration(
        "source-bounded-int",
        updates,
        actor=actor,
        logger=logger,
    )

    entry = logger.entries[0]
    assert len(entry.payload["changes"]) == _AUDIT_MAX_CHANGES
    assert len(entry.payload["changes"]["long_value"]) == _AUDIT_MAX_TEXT_LENGTH
    assert len(entry.payload["changes"]["nested"]["items"]) <= 10
