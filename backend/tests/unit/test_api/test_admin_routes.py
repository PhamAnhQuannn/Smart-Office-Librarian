from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.v1.routes.admin_routes import (
    AdminRouteError,
    delete_source_configuration,
    update_source_configuration,
    update_threshold_configuration,
)
from app.core.logging import AUDIT_LOG_RETENTION_DAYS, InMemoryStructuredLogger, REDACTED


def _admin_actor() -> SimpleNamespace:
    return SimpleNamespace(user_id="admin-1", role="admin")


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
