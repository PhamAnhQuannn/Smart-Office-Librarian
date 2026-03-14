"""Focused admin-route helpers for audit logging and retention foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.logging import AUDIT_LOG_RETENTION_DAYS, InMemoryStructuredLogger


@dataclass(frozen=True)
class AdminRouteError(Exception):
    error_code: str
    message: str
    status_code: int

    def __str__(self) -> str:
        return self.message


def _get_actor_value(actor: Any, field_name: str) -> Any:
    if isinstance(actor, Mapping):
        return actor.get(field_name)
    return getattr(actor, field_name, None)


def _normalize_role(role: Any) -> str:
    if hasattr(role, "value"):
        return str(role.value).lower()
    return str(role).lower()


def _require_admin(actor: Any) -> tuple[str, Any]:
    actor_id = _get_actor_value(actor, "user_id") or _get_actor_value(actor, "id")
    if not actor_id:
        raise AdminRouteError("UNAUTHENTICATED", "Authentication required", 401)

    role = _get_actor_value(actor, "role")
    if _normalize_role(role) != "admin":
        raise AdminRouteError("FORBIDDEN", "Admin role required", 403)

    return str(actor_id), role


def update_source_configuration(
    source_id: str,
    updates: Mapping[str, Any],
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    actor_id, actor_role = _require_admin(actor)
    normalized_updates = dict(updates)
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="source",
        action="updated",
        resource_id=source_id,
        changes=normalized_updates,
    )
    return {
        "source_id": source_id,
        "updated_fields": sorted(normalized_updates.keys()),
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def delete_source_configuration(
    source_id: str,
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    actor_id, actor_role = _require_admin(actor)
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="source",
        action="deleted",
        resource_id=source_id,
        changes={"source_id": source_id},
    )
    return {
        "source_id": source_id,
        "status": "queued_for_deletion",
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def update_threshold_configuration(
    *,
    namespace: str,
    index_version: int,
    threshold: float,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    if threshold < 0.0 or threshold > 1.0:
        raise AdminRouteError("VALIDATION_ERROR", "Threshold must be between 0.0 and 1.0", 400)

    actor_id, actor_role = _require_admin(actor)
    resource_id = f"{namespace}:{index_version}"
    changes = {
        "namespace": namespace,
        "index_version": index_version,
        "threshold": threshold,
    }
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="threshold",
        action="updated",
        resource_id=resource_id,
        changes=changes,
    )
    return {
        "namespace": namespace,
        "index_version": index_version,
        "threshold": threshold,
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def update_role_assignment(
    target_user_id: str,
    new_role: str,
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    """Emit an audit event when an admin assigns a role to a user."""
    actor_id, actor_role = _require_admin(actor)
    changes = {
        "target_user_id": target_user_id,
        "new_role": new_role,
    }
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="role",
        action="assigned",
        resource_id=target_user_id,
        changes=changes,
    )
    return {
        "target_user_id": target_user_id,
        "new_role": new_role,
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }
