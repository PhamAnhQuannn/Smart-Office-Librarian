from __future__ import annotations

from types import SimpleNamespace

from app.api.v1.routes.admin_routes import (
    update_source_configuration,
    update_threshold_configuration,
)
from app.core.logging import AUDIT_LOG_RETENTION_DAYS, InMemoryStructuredLogger


def test_admin_source_and_threshold_changes_append_audit_entries() -> None:
    logger = InMemoryStructuredLogger()
    actor = SimpleNamespace(user_id="admin-1", role="admin")

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
