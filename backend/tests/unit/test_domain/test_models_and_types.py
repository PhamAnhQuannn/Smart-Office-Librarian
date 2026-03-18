"""Unit tests for domain model dataclasses."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.models import (
    BudgetStatus,
    Chunk,
    EvaluationResult,
    Feedback,
    IngestRun,
    QueryLog,
    Source,
    ThresholdConfig,
    User,
)
from app.types import (
    ConfidenceLevel,
    GenerationMode,
    Page,
    RefusalReason,
    RetrievalHit,
    RetrievalResult,
)


# ── User ─────────────────────────────────────────────────────────────────────


class TestUser:
    def test_is_admin_true_for_admin_role(self) -> None:
        user = User(id="u1", email="admin@example.com", role="admin")
        assert user.is_admin is True

    def test_is_admin_false_for_user_role(self) -> None:
        user = User(id="u2", email="user@example.com", role="user")
        assert user.is_admin is False

    def test_is_active_default(self) -> None:
        user = User(id="u3", email="a@b.com", role="user")
        assert user.is_active is True

    def test_allowed_namespaces_default_empty(self) -> None:
        user = User(id="u4", email="a@b.com", role="user")
        assert user.allowed_namespaces == []

    def test_fields_stored_correctly(self) -> None:
        now = datetime.now(timezone.utc)
        user = User(
            id="u5",
            email="test@example.com",
            role="user",
            is_active=False,
            created_at=now,
            allowed_namespaces=["dev", "prod"],
        )
        assert user.id == "u5"
        assert user.email == "test@example.com"
        assert user.is_active is False
        assert user.created_at == now
        assert user.allowed_namespaces == ["dev", "prod"]


# ── Source ────────────────────────────────────────────────────────────────────


class TestSource:
    def test_defaults(self) -> None:
        src = Source(id="s1", repo="org/repo", file_path="README.md")
        assert src.visibility == "private"
        assert src.source_url is None
        assert src.last_indexed_sha is None

    def test_all_fields(self) -> None:
        src = Source(
            id="s2",
            repo="org/repo",
            file_path="docs/guide.md",
            source_url="https://github.com/org/repo/blob/main/docs/guide.md",
            visibility="public",
            last_indexed_sha="abc123",
        )
        assert src.repo == "org/repo"
        assert src.visibility == "public"
        assert src.last_indexed_sha == "abc123"


# ── Chunk ─────────────────────────────────────────────────────────────────────


class TestChunk:
    def test_defaults(self) -> None:
        chunk = Chunk(
            id="c1",
            source_id="s1",
            vector_id="vec-001",
            text="Hello world",
        )
        assert chunk.namespace == "dev"
        assert chunk.simhash is None
        assert chunk.start_line is None
        assert chunk.end_line is None

    def test_fields_stored(self) -> None:
        chunk = Chunk(
            id="c2",
            source_id="s1",
            vector_id="vec-002",
            text="Some text",
            namespace="prod",
            simhash="deadbeef1234",
            start_line=10,
            end_line=20,
        )
        assert chunk.namespace == "prod"
        assert chunk.start_line == 10
        assert chunk.end_line == 20


# ── ThresholdConfig ───────────────────────────────────────────────────────────


class TestThresholdConfig:
    def test_fields(self) -> None:
        tc = ThresholdConfig(
            id="t1",
            namespace="dev",
            index_version=1,
            threshold=0.75,
            updated_by="admin-uuid",
        )
        assert tc.threshold == 0.75
        assert tc.updated_by == "admin-uuid"

    def test_updated_by_optional(self) -> None:
        tc = ThresholdConfig(id="t2", namespace="dev", index_version=1, threshold=0.6)
        assert tc.updated_by is None


# ── QueryLog ──────────────────────────────────────────────────────────────────


class TestQueryLog:
    def test_defaults(self) -> None:
        ql = QueryLog(
            id="q1",
            user_id="u1",
            query_text="What is embedlyzer?",
            mode="answer",
        )
        assert ql.namespace == "dev"
        assert ql.index_version == 1
        assert ql.confidence is None
        assert ql.sources is None

    def test_all_optional_fields(self) -> None:
        ql = QueryLog(
            id="q2",
            user_id=None,
            query_text="test",
            mode="refusal",
            refusal_reason="below_threshold",
            confidence="LOW",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert ql.user_id is None
        assert ql.refusal_reason == "below_threshold"
        assert ql.prompt_tokens == 100


# ── Feedback ──────────────────────────────────────────────────────────────────


class TestFeedback:
    def test_fields(self) -> None:
        fb = Feedback(
            id="f1",
            query_log_id="q1",
            vote="up",
            user_id="u1",
            comment="Very helpful!",
        )
        assert fb.vote == "up"
        assert fb.comment == "Very helpful!"

    def test_optional_user_and_comment(self) -> None:
        fb = Feedback(id="f2", query_log_id="q1", vote="down")
        assert fb.user_id is None
        assert fb.comment is None


# ── IngestRun ─────────────────────────────────────────────────────────────────


class TestIngestRun:
    def test_defaults(self) -> None:
        run = IngestRun(id="r1", repo="org/repo")
        assert run.branch == "main"
        assert run.status == "queued"
        assert run.ingested_documents == 0
        assert run.error_message is None

    def test_completed_fields(self) -> None:
        now = datetime.now(timezone.utc)
        run = IngestRun(
            id="r2",
            repo="org/repo",
            branch="feat/x",
            status="completed",
            ingested_documents=42,
            skipped_duplicates=5,
            completed_at=now,
        )
        assert run.status == "completed"
        assert run.ingested_documents == 42
        assert run.completed_at == now


# ── EvaluationResult ──────────────────────────────────────────────────────────


class TestEvaluationResult:
    def test_passed(self) -> None:
        er = EvaluationResult(
            id="e1",
            dataset_name="golden_v1",
            question="What is RAG?",
            passed=True,
            cosine_score=0.91,
        )
        assert er.passed is True
        assert er.cosine_score == 0.91

    def test_optional_fields(self) -> None:
        er = EvaluationResult(
            id="e2",
            dataset_name="golden_v1",
            question="What?",
            passed=False,
        )
        assert er.expected_answer is None
        assert er.actual_answer is None
        assert er.cosine_score is None


# ── BudgetStatus ──────────────────────────────────────────────────────────────


class TestBudgetStatus:
    def test_not_exhausted(self) -> None:
        b = BudgetStatus.from_usage(budget=1_000_000, used=800_000)
        assert b.tokens_used == 800_000
        assert b.tokens_remaining == 200_000
        assert b.is_exhausted is False

    def test_exactly_exhausted(self) -> None:
        b = BudgetStatus.from_usage(budget=500_000, used=500_000)
        assert b.is_exhausted is True
        assert b.tokens_remaining == 0

    def test_over_budget(self) -> None:
        b = BudgetStatus.from_usage(budget=100_000, used=120_000)
        assert b.is_exhausted is True
        assert b.tokens_remaining == 0

    def test_zero_usage(self) -> None:
        b = BudgetStatus.from_usage(budget=1_000_000, used=0)
        assert b.tokens_used == 0
        assert b.tokens_remaining == 1_000_000
        assert b.is_exhausted is False


# ── ConfidenceLevel ───────────────────────────────────────────────────────────


class TestConfidenceLevel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.90, ConfidenceLevel.HIGH),
            (0.85, ConfidenceLevel.HIGH),
            (0.80, ConfidenceLevel.MEDIUM),
            (0.70, ConfidenceLevel.MEDIUM),
            (0.65, ConfidenceLevel.LOW),
            (0.00, ConfidenceLevel.LOW),
        ],
    )
    def test_from_score(self, score: float, expected: ConfidenceLevel) -> None:
        assert ConfidenceLevel.from_score(score) == expected

    def test_custom_thresholds(self) -> None:
        assert ConfidenceLevel.from_score(0.95, high_threshold=0.99, low_threshold=0.80) == ConfidenceLevel.MEDIUM

    def test_string_values(self) -> None:
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"


# ── GenerationMode / RefusalReason ────────────────────────────────────────────


class TestGenerationMode:
    def test_values(self) -> None:
        assert GenerationMode.ANSWER.value == "answer"
        assert GenerationMode.REFUSAL.value == "refusal"
        assert GenerationMode.RETRIEVAL_ONLY.value == "retrieval_only"

    def test_string_comparison(self) -> None:
        assert GenerationMode.ANSWER == "answer"


class TestRefusalReason:
    def test_all_reasons_have_string_values(self) -> None:
        for reason in RefusalReason:
            assert isinstance(reason.value, str)


# ── Page ─────────────────────────────────────────────────────────────────────


class TestPage:
    def test_has_next_true(self) -> None:
        page: Page[int] = Page(items=[1, 2, 3], total=10, page=1, page_size=3)
        assert page.has_next is True

    def test_has_next_false_last_page(self) -> None:
        page: Page[int] = Page(items=[10], total=10, page=4, page_size=3)
        assert page.has_next is False

    def test_has_prev_false_on_first_page(self) -> None:
        page: Page[int] = Page(items=[1], total=5, page=1, page_size=5)
        assert page.has_prev is False

    def test_has_prev_true_on_later_page(self) -> None:
        page: Page[int] = Page(items=[6, 7, 8], total=10, page=2, page_size=5)
        assert page.has_prev is True

    def test_empty_page(self) -> None:
        page: Page[str] = Page(items=[], total=0)
        assert page.has_next is False
        assert page.has_prev is False


# ── RetrievalHit / RetrievalResult ────────────────────────────────────────────


class TestRetrievalResult:
    def _make_hit(self, score: float) -> RetrievalHit:
        return RetrievalHit(vector_id="v1", score=score, namespace="dev", text="sample")

    def test_top_score_empty(self) -> None:
        result = RetrievalResult(hits=[], threshold_used=0.75)
        assert result.top_score == 0.0

    def test_top_score_uses_first_hit(self) -> None:
        hits = [self._make_hit(0.90), self._make_hit(0.70)]
        result = RetrievalResult(hits=hits, threshold_used=0.75)
        assert result.top_score == 0.90

    def test_passed_threshold_true(self) -> None:
        r = RetrievalResult(hits=[self._make_hit(0.80)], threshold_used=0.75)
        assert r.passed_threshold is True

    def test_passed_threshold_false(self) -> None:
        r = RetrievalResult(hits=[self._make_hit(0.60)], threshold_used=0.75)
        assert r.passed_threshold is False

    def test_passed_threshold_false_when_empty(self) -> None:
        r = RetrievalResult(hits=[], threshold_used=0.75)
        assert r.passed_threshold is False
