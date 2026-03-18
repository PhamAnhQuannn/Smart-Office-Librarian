"""Unit tests for app.core.errors."""
from __future__ import annotations

import pytest

from app.core.errors import (
    AppError,
    AuthError,
    BudgetExhaustedError,
    ConfigurationError,
    ForbiddenError,
    IndexSafetyError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)


def test_app_error_message_and_details() -> None:
    err = AppError("something went wrong", details={"field": "query"})
    assert err.message == "something went wrong"
    assert err.details == {"field": "query"}
    assert str(err) == "something went wrong"


def test_app_error_default_details() -> None:
    err = AppError("bare error")
    assert err.details == {}


class TestStatusCodes:
    def test_not_found(self) -> None:
        assert NotFoundError.status_code == 404
        assert NotFoundError.error_code == "NOT_FOUND"

    def test_validation_error(self) -> None:
        assert ValidationError.status_code == 422
        assert ValidationError.error_code == "VALIDATION_ERROR"

    def test_auth_error(self) -> None:
        assert AuthError.status_code == 401

    def test_forbidden_error(self) -> None:
        assert ForbiddenError.status_code == 403
        assert ForbiddenError.error_code == "FORBIDDEN"

    def test_rate_limit(self) -> None:
        assert RateLimitError.status_code == 429

    def test_upstream_error(self) -> None:
        assert UpstreamError.status_code == 502

    def test_configuration_error(self) -> None:
        assert ConfigurationError.status_code == 500

    def test_index_safety_error(self) -> None:
        assert IndexSafetyError.status_code == 409

    def test_budget_exhausted_error(self) -> None:
        assert BudgetExhaustedError.status_code == 402


def test_all_errors_are_app_error_subclasses() -> None:
    for cls in [
        NotFoundError, ValidationError, AuthError, ForbiddenError,
        RateLimitError, UpstreamError, ConfigurationError,
        IndexSafetyError, BudgetExhaustedError,
    ]:
        err = cls("msg")
        assert isinstance(err, AppError)
        assert isinstance(err, Exception)


def test_error_can_be_raised_and_caught() -> None:
    with pytest.raises(AppError) as exc_info:
        raise NotFoundError("resource missing")
    assert exc_info.value.status_code == 404
    assert "resource missing" in str(exc_info.value)
