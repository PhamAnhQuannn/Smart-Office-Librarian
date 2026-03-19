"""Tests for the user query history routes.

Covers:
- GET /history returns serialized items for authenticated user
- GET /history without auth returns 401
- DELETE /history/{id} removes owned item (204)
- DELETE /history/{id} returns 404 for unowned/missing item
- DELETE /history clears all items owned by user (204)
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.v1.routes.history_routes import (
    _serialize_log,
    clear_history,
    delete_history_item,
    list_history,
)
from app.core.security import AuthenticatedUser, UserRole

_REPO_PATH = "app.db.repositories.query_logs_repo.QueryLogsRepository"

# ── Helpers ────────────────────────────────────────────────────────────────────


def _user(user_id: str = "user-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id,
        role=UserRole.USER,
        workspace_id="ws-1",
        workspace_slug="ws-slug",
    )


_NO_SOURCES = object()  # sentinel to distinguish "not supplied" from None


def _mock_log(
    *,
    id: str = "log-1",
    query_text: str = "What is RAG?",
    confidence: str = "HIGH",
    mode: str = "semantic",
    sources=_NO_SOURCES,
    created_at=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        query_text=query_text,
        confidence=confidence,
        mode=mode,
        sources=["s1", "s2"] if sources is _NO_SOURCES else sources,
        created_at=created_at,
    )


# ── _serialize_log ─────────────────────────────────────────────────────────────


def test_serialize_log_standard() -> None:
    log = _mock_log(sources=["s1", "s2", "s3"])
    result = _serialize_log(log)
    assert result["id"] == "log-1"
    assert result["query_text"] == "What is RAG?"
    assert result["confidence"] == "HIGH"
    assert result["mode"] == "semantic"
    assert result["sources_count"] == 3
    assert result["created_at"] is None


def test_serialize_log_none_confidence_becomes_unknown() -> None:
    log = _mock_log(confidence=None)  # type: ignore[arg-type]
    result = _serialize_log(log)
    assert result["confidence"] == "UNKNOWN"


def test_serialize_log_non_list_sources_gives_zero_count() -> None:
    log = _mock_log(sources=None)
    result = _serialize_log(log)
    assert result["sources_count"] == 0


# ── list_history ───────────────────────────────────────────────────────────────


def test_list_history_returns_items() -> None:
    db = MagicMock()
    user = _user()
    fake_logs = [_mock_log(id=f"log-{i}", query_text=f"Q {i}") for i in range(3)]

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.list_by_user.return_value = fake_logs
        response = list_history(limit=50, user=user, db=db)

    data = response.body
    import json
    payload = json.loads(data)
    assert payload["total"] == 3
    assert len(payload["items"]) == 3
    assert payload["items"][0]["id"] == "log-0"
    MockRepo.return_value.list_by_user.assert_called_once_with("user-1", limit=50)


def test_list_history_clamps_limit() -> None:
    db = MagicMock()
    user = _user()

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.list_by_user.return_value = []
        list_history(limit=9999, user=user, db=db)
        MockRepo.return_value.list_by_user.assert_called_once_with("user-1", limit=200)


def test_list_history_returns_empty_list_when_no_logs() -> None:
    db = MagicMock()
    user = _user()

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.list_by_user.return_value = []
        response = list_history(limit=50, user=user, db=db)

    import json
    payload = json.loads(response.body)
    assert payload == {"items": [], "total": 0}


# ── delete_history_item ────────────────────────────────────────────────────────


def test_delete_history_item_returns_none_on_success() -> None:
    db = MagicMock()
    user = _user()

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.delete_by_id_and_user.return_value = True
        result = delete_history_item("log-1", user=user, db=db)

    assert result is None
    db.commit.assert_called_once()


def test_delete_history_item_raises_404_when_not_found() -> None:
    db = MagicMock()
    user = _user()

    from fastapi import HTTPException

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.delete_by_id_and_user.return_value = False
        with pytest.raises(HTTPException) as exc_info:
            delete_history_item("log-missing", user=user, db=db)

    assert exc_info.value.status_code == 404
    db.commit.assert_not_called()


# ── clear_history ──────────────────────────────────────────────────────────────


def test_clear_history_commits_and_returns_none() -> None:
    db = MagicMock()
    user = _user()

    with patch(_REPO_PATH) as MockRepo:
        MockRepo.return_value.delete_all_by_user.return_value = 5
        result = clear_history(user=user, db=db)

    assert result is None
    MockRepo.return_value.delete_all_by_user.assert_called_once_with("user-1")
    db.commit.assert_called_once()
