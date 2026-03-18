"""RBAC service: namespace-level permission enforcement.

FR-1.3 specifies that non-admin users can only query namespaces they have been
explicitly granted access to.  Admins have access to all namespaces.
"""

from __future__ import annotations

from typing import Any

from app.core.security import AuthenticatedUser, UserRole


class RBACService:
    """Resolves per-user namespace access and builds Pinecone filter dicts."""

    def __init__(self, users_repo: Any | None = None) -> None:
        self._repo = users_repo

    # ── access check ──────────────────────────────────────────────────────────

    def can_access_namespace(self, user: AuthenticatedUser, namespace: str) -> bool:
        """Return True if the user is allowed to query the given namespace."""
        if user.role == UserRole.ADMIN:
            return True
        allowed = self._get_allowed_namespaces(user.user_id)
        return namespace in allowed

    def assert_namespace_access(self, user: AuthenticatedUser, namespace: str) -> None:
        """Raise ForbiddenError if the user cannot access the namespace."""
        if not self.can_access_namespace(user, namespace):
            from app.core.errors import ForbiddenError
            raise ForbiddenError(f"User does not have access to namespace '{namespace}'")

    # ── filter builder ────────────────────────────────────────────────────────

    def build_rbac_filter(self, user: AuthenticatedUser) -> dict[str, Any] | None:
        """Return a Pinecone metadata filter dict, or None for admins."""
        if user.role == UserRole.ADMIN:
            return None  # admins see everything
        allowed = self._get_allowed_namespaces(user.user_id)
        if not allowed:
            # user with no explicit grants cannot see any results
            return {"namespace": {"$in": []}}
        return {"namespace": {"$in": list(allowed)}}

    # ── internals ────────────────────────────────────────────────────────────

    def _get_allowed_namespaces(self, user_id: str) -> set[str]:
        """Look up user namespace grants from DB, falling back to empty set."""
        if self._repo is None:
            return set()
        user_model = None
        if hasattr(self._repo, "get_by_user_id"):
            user_model = self._repo.get_by_user_id(user_id)
        elif hasattr(self._repo, "get"):
            user_model = self._repo.get(user_id)
        if user_model is None:
            return set()
        allowed = getattr(user_model, "allowed_namespaces", None)
        if isinstance(allowed, list):
            return set(allowed)
        return set()
