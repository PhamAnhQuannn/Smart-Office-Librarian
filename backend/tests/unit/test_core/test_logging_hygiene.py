from __future__ import annotations

from app.core.logging import REDACTED, safe_error_message, sanitize_log_data
from app.main import _error_response


def test_logging_hygiene_redacts_sensitive_keys_recursively() -> None:
    payload = {
        "token": "abc",
        "nested": {
            "api_key": "xyz",
            "allowed": "value",
        },
    }

    sanitized = sanitize_log_data(payload)

    assert sanitized["token"] == REDACTED
    assert sanitized["nested"]["api_key"] == REDACTED
    assert sanitized["nested"]["allowed"] == "value"


def test_logging_hygiene_redacts_bearer_and_jwt_in_free_text() -> None:
    text = "Authorization failed for Bearer abc.def.ghi and jwt aaa.bbb.ccc"
    sanitized = sanitize_log_data(text)

    assert "abc.def.ghi" not in sanitized
    assert "aaa.bbb.ccc" not in sanitized
    assert REDACTED in sanitized


def test_logging_hygiene_safe_error_message_redacts_provider_tokens() -> None:
    message = "github token leaked: ghp_1234567890abcdefghij"
    sanitized = safe_error_message(message)

    assert "ghp_1234567890abcdefghij" not in sanitized
    assert REDACTED in sanitized


def test_logging_hygiene_error_response_redacts_message_and_details() -> None:
    response = _error_response(
        status_code=401,
        error_code="UNAUTHENTICATED",
        message="invalid Bearer abc.def.ghi",
        details={"authorization": "Bearer abc.def.ghi", "context": "safe"},
    )

    assert response["body"]["message"].find("abc.def.ghi") == -1
    assert response["body"]["details"]["authorization"] == REDACTED
    assert response["body"]["details"]["context"] == "safe"
