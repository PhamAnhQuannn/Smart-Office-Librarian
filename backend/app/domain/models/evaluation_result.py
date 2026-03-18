"""Domain model: EvaluationResult."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EvaluationResult:
    id: str
    dataset_name: str
    question: str
    passed: bool
    expected_answer: str | None = None
    actual_answer: str | None = None
    cosine_score: float | None = None
    latency_ms: float | None = None
    created_at: datetime | None = None
