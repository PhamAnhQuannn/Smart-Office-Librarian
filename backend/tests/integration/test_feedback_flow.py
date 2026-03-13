from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.core.metrics import FEEDBACK_TOTAL
from app.main import EmbedlyzerApp

JWT_SECRET = "test-secret"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(*, user_id: str = "user-1", role: str = "user", exp: int | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + 3600 if exp is None else exp,
    }
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def test_feedback_upvote_is_accepted_and_counted() -> None:
    app = EmbedlyzerApp()

    response = app.feedback_request(
        authorization=f"Bearer {_make_jwt(user_id='feedback-user')}",
        jwt_secret=JWT_SECRET,
        query_log_id="query-123",
        vote="up",
    )

    assert response["status_code"] == 202
    assert response["body"] == {
        "status": "accepted",
        "query_log_id": "query-123",
        "vote": "up",
        "review_required": False,
    }
    assert app.metrics.get_counter(FEEDBACK_TOTAL, vote="up") == 1
    assert app.logger.entries == []


def test_feedback_downvote_creates_review_log_and_redacts_sensitive_metadata() -> None:
    app = EmbedlyzerApp()

    response = app.feedback_request(
        authorization=f"Bearer {_make_jwt(user_id='feedback-reviewer')}",
        jwt_secret=JWT_SECRET,
        query_log_id="query-456",
        vote="down",
        comment="answer missed the deployment step",
        metadata={
            "authorization": "Bearer should-not-appear",
            "nested": {"api_key": "hidden"},
            "visible_context": "retained",
        },
    )

    assert response["status_code"] == 202
    assert response["body"]["review_required"] is True
    assert app.metrics.get_counter(FEEDBACK_TOTAL, vote="down") == 1

    entry = app.logger.entries[-1]
    assert entry.event_type == "feedback.downvote"
    assert entry.payload["metadata"]["authorization"] == "***REDACTED***"
    assert entry.payload["metadata"]["nested"]["api_key"] == "***REDACTED***"
    assert entry.payload["metadata"]["visible_context"] == "retained"
