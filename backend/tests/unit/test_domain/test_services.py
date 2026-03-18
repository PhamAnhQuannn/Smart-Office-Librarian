"""Unit tests for domain services."""
from __future__ import annotations

import pytest

from app.core.config import reset_settings
from app.core.errors import ForbiddenError
from app.core.security import AuthenticatedUser, UserRole
from app.domain.services.cost_service import CostService
from app.domain.services.threshold_service import ThresholdService
from app.domain.services.rbac_service import RBACService


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

def _make_user(role: UserRole = UserRole.USER, namespaces: list[str] | None = None) -> AuthenticatedUser:
    user = AuthenticatedUser(user_id="user-123", role=role)
    return user


class _FakeThresholdRecord:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold


class _FakeThresholdsRepo:
    def __init__(self, record: _FakeThresholdRecord | None = None) -> None:
        self._record = record
        self.upserted: dict | None = None

    def get_for_namespace(self, namespace: str, index_version: int) -> _FakeThresholdRecord | None:
        return self._record

    def upsert(self, *, namespace: str, index_version: int, threshold: float, updated_by: str | None) -> _FakeThresholdRecord:
        self.upserted = dict(namespace=namespace, index_version=index_version, threshold=threshold, updated_by=updated_by)
        return _FakeThresholdRecord(threshold)


class _FakeUserModel:
    def __init__(self, namespaces: list[str]) -> None:
        self.allowed_namespaces = namespaces


class _FakeUsersRepo:
    def __init__(self, namespaces_by_user: dict[str, list[str]] | None = None) -> None:
        self._map = namespaces_by_user or {}

    def get_by_user_id(self, user_id: str) -> _FakeUserModel | None:
        if user_id in self._map:
            return _FakeUserModel(self._map[user_id])
        return None


# ---------------------------------------------------------------------------
# ThresholdService
# ---------------------------------------------------------------------------

class TestThresholdService:
    def test_returns_config_default_when_no_repo(self) -> None:
        reset_settings()
        svc = ThresholdService(thresholds_repo=None)
        t = svc.get_threshold(namespace="default", index_version=1)
        assert 0.0 <= t <= 1.0

    def test_returns_db_value_when_repo_has_record(self) -> None:
        repo = _FakeThresholdsRepo(record=_FakeThresholdRecord(0.82))
        svc = ThresholdService(thresholds_repo=repo)
        assert svc.get_threshold(namespace="ns", index_version=1) == pytest.approx(0.82)

    def test_falls_back_to_config_when_repo_returns_none(self) -> None:
        repo = _FakeThresholdsRepo(record=None)
        svc = ThresholdService(thresholds_repo=repo)
        t = svc.get_threshold(namespace="ns", index_version=1)
        assert 0.0 <= t <= 1.0

    def test_update_threshold_persists_value(self) -> None:
        repo = _FakeThresholdsRepo()
        svc = ThresholdService(thresholds_repo=repo)
        result = svc.update_threshold(namespace="ns", index_version=1, threshold=0.65)
        assert result == pytest.approx(0.65)
        assert repo.upserted is not None
        assert repo.upserted["threshold"] == pytest.approx(0.65)

    def test_update_threshold_rejects_out_of_range(self) -> None:
        repo = _FakeThresholdsRepo()
        svc = ThresholdService(thresholds_repo=repo)
        with pytest.raises(ValueError):
            svc.update_threshold(namespace="ns", index_version=1, threshold=1.5)

    def test_update_threshold_raises_without_repo(self) -> None:
        svc = ThresholdService(thresholds_repo=None)
        with pytest.raises(RuntimeError):
            svc.update_threshold(namespace="ns", index_version=1, threshold=0.5)


# ---------------------------------------------------------------------------
# CostService
# ---------------------------------------------------------------------------

class TestCostService:
    def test_estimate_zero_tokens(self) -> None:
        cost = CostService.estimate_query_cost(
            prompt_tokens=0, completion_tokens=0, embedding_tokens=0
        )
        assert cost == 0.0

    def test_estimate_positive_tokens(self) -> None:
        cost = CostService.estimate_query_cost(
            prompt_tokens=1000, completion_tokens=200, embedding_tokens=500
        )
        assert cost > 0.0

    def test_budget_not_exhausted_initially(self) -> None:
        svc = CostService(monthly_token_budget=100_000)
        assert not svc.is_budget_exhausted()

    def test_budget_exhausted_after_recording(self) -> None:
        svc = CostService(monthly_token_budget=100)
        svc.record_usage(tokens=100)
        assert svc.is_budget_exhausted()

    def test_budget_not_exhausted_below_limit(self) -> None:
        svc = CostService(monthly_token_budget=1000)
        svc.record_usage(tokens=999)
        assert not svc.is_budget_exhausted()

    def test_record_usage_accumulates(self) -> None:
        svc = CostService(monthly_token_budget=100)
        svc.record_usage(tokens=40)
        svc.record_usage(tokens=61)
        assert svc.is_budget_exhausted()


# ---------------------------------------------------------------------------
# RBACService
# ---------------------------------------------------------------------------

class TestRBACService:
    def test_admin_can_access_any_namespace(self) -> None:
        svc = RBACService(users_repo=_FakeUsersRepo())
        admin = _make_user(role=UserRole.ADMIN)
        assert svc.can_access_namespace(admin, "any-namespace")

    def test_user_with_access_allowed(self) -> None:
        repo = _FakeUsersRepo({"user-123": ["ns-a", "ns-b"]})
        svc = RBACService(users_repo=repo)
        user = _make_user(role=UserRole.USER)
        assert svc.can_access_namespace(user, "ns-a")

    def test_user_without_access_denied(self) -> None:
        repo = _FakeUsersRepo({"user-123": ["ns-a"]})
        svc = RBACService(users_repo=repo)
        user = _make_user(role=UserRole.USER)
        assert not svc.can_access_namespace(user, "restricted")

    def test_assert_namespace_access_raises_for_denied(self) -> None:
        repo = _FakeUsersRepo({"user-123": []})
        svc = RBACService(users_repo=repo)
        user = _make_user(role=UserRole.USER)
        with pytest.raises(ForbiddenError):
            svc.assert_namespace_access(user, "secret-namespace")

    def test_build_rbac_filter_admin_returns_none(self) -> None:
        svc = RBACService()
        admin = _make_user(role=UserRole.ADMIN)
        assert svc.build_rbac_filter(admin) is None

    def test_build_rbac_filter_user_returns_dict(self) -> None:
        repo = _FakeUsersRepo({"user-123": ["ns-x", "ns-y"]})
        svc = RBACService(users_repo=repo)
        user = _make_user(role=UserRole.USER)
        f = svc.build_rbac_filter(user)
        assert f is not None
        assert isinstance(f, dict)
