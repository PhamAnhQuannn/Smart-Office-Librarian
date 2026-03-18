"""Integration tests for RBAC namespace filtering.

Verifies that:
- Users can only access namespaces they are explicitly granted.
- Admin users bypass all namespace restrictions.
- Users with no grants receive an empty filter (no results).
- The RBAC filter dict has the correct Pinecone shape.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.errors import ForbiddenError
from app.core.security import AuthenticatedUser, UserRole
from app.domain.services.rbac_service import RBACService


# ---------------------------------------------------------------------------
# Fake repository
# ---------------------------------------------------------------------------

class _FakeUsersRepo:
    def __init__(self, grants: dict[str, list[str]]) -> None:
        self._grants = grants  # user_id -> [namespace, ...]

    def get_by_user_id(self, user_id: str) -> Any:
        namespaces = self._grants.get(user_id, [])

        class _FakeUser:
            allowed_namespaces = namespaces

        return _FakeUser()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(grants: dict[str, list[str]] | None = None) -> RBACService:
    repo = _FakeUsersRepo(grants or {})
    return RBACService(users_repo=repo)


def _user(user_id: str = "u1", role: UserRole = UserRole.USER) -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, role=role)


def _admin(user_id: str = "admin") -> AuthenticatedUser:
    return AuthenticatedUser(user_id=user_id, role=UserRole.ADMIN)


# ---------------------------------------------------------------------------
# can_access_namespace
# ---------------------------------------------------------------------------

class TestCanAccessNamespace:
    def test_admin_can_access_any_namespace(self) -> None:
        svc = _svc()
        assert svc.can_access_namespace(_admin(), "secret-ns") is True

    def test_user_with_grant_can_access(self) -> None:
        svc = _svc({"u1": ["public", "eng"]})
        assert svc.can_access_namespace(_user("u1"), "eng") is True

    def test_user_without_grant_denied(self) -> None:
        svc = _svc({"u1": ["public"]})
        assert svc.can_access_namespace(_user("u1"), "secret-ns") is False

    def test_user_with_no_grants_denied(self) -> None:
        svc = _svc()
        assert svc.can_access_namespace(_user("u1"), "default") is False

    def test_admin_access_does_not_depend_on_grants(self) -> None:
        svc = _svc({"admin": ["only-this"]})
        assert svc.can_access_namespace(_admin("admin"), "some-other-ns") is True


# ---------------------------------------------------------------------------
# assert_namespace_access
# ---------------------------------------------------------------------------

class TestAssertNamespaceAccess:
    def test_raises_forbidden_for_denied_user(self) -> None:
        svc = _svc({"u1": ["public"]})
        with pytest.raises(ForbiddenError):
            svc.assert_namespace_access(_user("u1"), "restricted")

    def test_does_not_raise_for_granted_user(self) -> None:
        svc = _svc({"u1": ["public"]})
        svc.assert_namespace_access(_user("u1"), "public")  # no exception

    def test_does_not_raise_for_admin(self) -> None:
        svc = _svc()
        svc.assert_namespace_access(_admin(), "any-ns")  # no exception

    def test_forbidden_message_contains_namespace(self) -> None:
        svc = _svc()
        with pytest.raises(ForbiddenError, match="restricted-ns"):
            svc.assert_namespace_access(_user("u1"), "restricted-ns")


# ---------------------------------------------------------------------------
# build_rbac_filter
# ---------------------------------------------------------------------------

class TestBuildRbacFilter:
    def test_admin_returns_none_filter(self) -> None:
        svc = _svc()
        assert svc.build_rbac_filter(_admin()) is None

    def test_user_with_grants_returns_namespace_in_filter(self) -> None:
        svc = _svc({"u1": ["eng", "docs"]})
        f = svc.build_rbac_filter(_user("u1"))
        assert f is not None
        assert set(f["namespace"]["$in"]) == {"eng", "docs"}

    def test_user_with_no_grants_returns_empty_in_filter(self) -> None:
        svc = _svc()
        f = svc.build_rbac_filter(_user("u1"))
        assert f is not None
        assert f["namespace"]["$in"] == []

    def test_filter_structure_is_pinecone_compatible(self) -> None:
        svc = _svc({"u1": ["default"]})
        f = svc.build_rbac_filter(_user("u1"))
        assert f is not None
        assert "namespace" in f
        assert "$in" in f["namespace"]
        assert isinstance(f["namespace"]["$in"], list)

    def test_single_grant_produces_single_element_list(self) -> None:
        svc = _svc({"u1": ["only-ns"]})
        f = svc.build_rbac_filter(_user("u1"))
        assert f is not None
        assert len(f["namespace"]["$in"]) == 1
