"""Unit tests for Pydantic API schemas (v2)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.auth import LoginRequest, TokenResponse
from app.api.v1.schemas.common import ErrorResponse, HealthStatus, PaginationMeta
from app.api.v1.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.api.v1.schemas.ingest import IngestRequest, IngestResponse
from app.api.v1.schemas.query import QueryRequest, QueryResponse, SourceCitation
from app.api.v1.schemas.source import DeleteSourceResponse, SourceListResponse, SourceRecord


# ── Auth schemas ──────────────────────────────────────────────────────────────


class TestLoginRequest:
    def test_valid(self) -> None:
        req = LoginRequest(email="user@example.com", password="secret")
        assert req.email == "user@example.com"
        assert req.password == "secret"

    def test_email_is_plain_str_no_format_check(self) -> None:
        # email is typed as plain str — no EmailStr validation
        req = LoginRequest(email="not_an_email", password="pw")
        assert req.email == "not_an_email"

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com")  # type: ignore[call-arg]


class TestTokenResponse:
    def test_token_type_default_bearer(self) -> None:
        resp = TokenResponse(access_token="tok123", expires_in=3600)
        assert resp.token_type == "bearer"

    def test_custom_token_type(self) -> None:
        resp = TokenResponse(access_token="tok", expires_in=3600, token_type="JWT")
        assert resp.token_type == "JWT"

    def test_missing_expires_in_raises(self) -> None:
        with pytest.raises(ValidationError):
            TokenResponse(access_token="tok")  # type: ignore[call-arg]


# ── Common schemas ────────────────────────────────────────────────────────────


class TestErrorResponse:
    def test_valid(self) -> None:
        err = ErrorResponse(error="not_found", detail="Resource not found.")
        assert err.error == "not_found"
        assert err.detail == "Resource not found."

    def test_optional_fields_default_none(self) -> None:
        err = ErrorResponse(error="internal_error")
        assert err.detail is None
        assert err.request_id is None


class TestPaginationMeta:
    def test_fields(self) -> None:
        meta = PaginationMeta(total=100, page=2, page_size=25, has_next=True)
        assert meta.total == 100
        assert meta.has_next is True

    def test_missing_has_next_raises(self) -> None:
        with pytest.raises(ValidationError):
            PaginationMeta(total=10, page=1, page_size=5)  # type: ignore[call-arg]


class TestHealthStatus:
    def test_valid(self) -> None:
        h = HealthStatus(status="ok")
        assert h.status == "ok"

    def test_checks_optional(self) -> None:
        h = HealthStatus(status="degraded", checks={"db": True, "cache": False})
        assert h.checks["cache"] is False


# ── Query schemas ─────────────────────────────────────────────────────────────


class TestQueryRequest:
    def test_minimal(self) -> None:
        req = QueryRequest(query_text="What is RAG?")
        assert req.query_text == "What is RAG?"

    def test_stream_default(self) -> None:
        req = QueryRequest(query_text="test")
        assert req.stream is True

    def test_stream_false(self) -> None:
        req = QueryRequest(query_text="test", stream=False)
        assert req.stream is False

    def test_namespace_default(self) -> None:
        req = QueryRequest(query_text="test")
        assert req.namespace == "default"

    def test_missing_query_text_raises(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest()  # type: ignore[call-arg]

    def test_empty_query_text_raises(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(query_text="")


class TestSourceCitation:
    def test_fields(self) -> None:
        citation = SourceCitation(text="some excerpt", score=0.88)
        assert citation.score == 0.88
        assert citation.text == "some excerpt"

    def test_file_path_and_source_url_optional(self) -> None:
        citation = SourceCitation(text="excerpt", score=0.75)
        assert citation.file_path is None
        assert citation.source_url is None


class TestQueryResponse:
    def test_answer_mode(self) -> None:
        resp = QueryResponse(
            query_log_id="ql-1",
            mode="answer",
            answer_text="Because embeddings.",
            confidence="HIGH",
        )
        assert resp.mode == "answer"
        assert resp.answer_text == "Because embeddings."

    def test_sources_default_empty(self) -> None:
        resp = QueryResponse(query_log_id="ql-2", mode="refusal", refusal_reason="below_threshold")
        assert resp.sources == []
        assert resp.refusal_reason == "below_threshold"

    def test_missing_query_log_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            QueryResponse(mode="answer")  # type: ignore[call-arg]


# ── Ingest schemas ────────────────────────────────────────────────────────────


class TestIngestRequest:
    def test_defaults(self) -> None:
        req = IngestRequest()
        assert req.namespace == "default"
        assert req.force_reingest is False

    def test_with_file_path(self) -> None:
        req = IngestRequest(file_path="/data/docs", namespace="prod")
        assert req.file_path == "/data/docs"
        assert req.namespace == "prod"

    def test_with_source_url(self) -> None:
        req = IngestRequest(source_url="https://github.com/org/repo")
        assert req.source_url == "https://github.com/org/repo"


class TestIngestResponse:
    def test_fields(self) -> None:
        resp = IngestResponse(run_id="r123", status="queued", namespace="default")
        assert resp.run_id == "r123"
        assert resp.status == "queued"
        assert resp.namespace == "default"

    def test_message_default_empty(self) -> None:
        resp = IngestResponse(run_id="r1", status="queued", namespace="dev")
        assert resp.message == ""


# ── Feedback schemas ──────────────────────────────────────────────────────────


class TestFeedbackRequest:
    def test_valid_up(self) -> None:
        req = FeedbackRequest(query_log_id="q1", vote="up")
        assert req.vote == "up"

    def test_valid_down(self) -> None:
        req = FeedbackRequest(query_log_id="q1", vote="down")
        assert req.vote == "down"

    def test_invalid_vote_raises(self) -> None:
        with pytest.raises(ValidationError):
            FeedbackRequest(query_log_id="q1", vote="sideways")

    def test_comment_optional(self) -> None:
        req = FeedbackRequest(query_log_id="q1", vote="up")
        assert req.comment is None

    def test_with_comment(self) -> None:
        req = FeedbackRequest(query_log_id="q1", vote="up", comment="Great answer!")
        assert req.comment == "Great answer!"


class TestFeedbackResponse:
    def test_fields(self) -> None:
        resp = FeedbackResponse(feedback_id="f1", status="recorded")
        assert resp.feedback_id == "f1"


# ── Source schemas ────────────────────────────────────────────────────────────


class TestSourceRecord:
    def test_fields(self) -> None:
        src = SourceRecord(source_id="s1", namespace="prod")
        assert src.source_id == "s1"
        assert src.namespace == "prod"

    def test_optional_fields_default_none(self) -> None:
        src = SourceRecord(source_id="s2", namespace="dev")
        assert src.file_path is None
        assert src.source_url is None
        assert src.created_at is None

    def test_chunk_count_default_zero(self) -> None:
        src = SourceRecord(source_id="s3", namespace="dev")
        assert src.chunk_count == 0


class TestSourceListResponse:
    def test_defaults(self) -> None:
        resp = SourceListResponse()
        assert resp.sources == []
        assert resp.total == 0

    def test_with_items(self) -> None:
        src = SourceRecord(source_id="s1", namespace="dev")
        resp = SourceListResponse(sources=[src], total=1)
        assert len(resp.sources) == 1
        assert resp.total == 1


class TestDeleteSourceResponse:
    def test_defaults(self) -> None:
        resp = DeleteSourceResponse(source_id="s1")
        assert resp.ok is True
        assert resp.source_id == "s1"
        assert resp.message == ""

    def test_custom_message(self) -> None:
        resp = DeleteSourceResponse(source_id="s2", message="Deleted 12 chunks.")
        assert resp.message == "Deleted 12 chunks."
