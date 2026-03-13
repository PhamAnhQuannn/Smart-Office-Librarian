from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.stages.refusal_stage import RefusalStage


def _sources(count: int) -> list[dict[str, str]]:
    return [
        {
            "file_path": f"docs/file_{i}.md",
            "source_url": f"https://example.com/file_{i}.md",
            "start_line": i,
            "end_line": i + 10,
            "text": f"snippet {i}",
        }
        for i in range(1, count + 1)
    ]


def test_refusal_stage_refuses_when_score_below_threshold_with_top3_sources() -> None:
    stage = RefusalStage()

    decision = stage.run(
        primary_cosine_score=0.64,
        threshold=0.65,
        ranked_sources=_sources(5),
    )

    assert decision.refused is True
    assert decision.refusal_reason == "LOW_SIMILARITY"
    assert len(decision.sources) == 3
    assert [source["file_path"] for source in decision.sources] == [
        "docs/file_1.md",
        "docs/file_2.md",
        "docs/file_3.md",
    ]


def test_refusal_stage_allows_when_score_equals_threshold() -> None:
    stage = RefusalStage()

    decision = stage.run(
        primary_cosine_score=0.65,
        threshold=0.65,
        ranked_sources=_sources(2),
    )

    assert decision.refused is False
    assert decision.refusal_reason is None
    assert len(decision.sources) == 2


def test_refusal_stage_requires_threshold() -> None:
    stage = RefusalStage()

    with pytest.raises(ValueError, match="threshold is required"):
        stage.run(
            primary_cosine_score=0.5,
            threshold=None,
            ranked_sources=_sources(1),
        )


def test_refusal_stage_has_no_internal_default_threshold() -> None:
    stage = RefusalStage()

    with pytest.raises(TypeError):
        stage.run(
            primary_cosine_score=0.7,
            ranked_sources=_sources(1),
        )
