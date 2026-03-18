"""Generation-related enumerations and types."""
from __future__ import annotations

from enum import Enum


class GenerationMode(str, Enum):
    ANSWER = "answer"
    REFUSAL = "refusal"
    RETRIEVAL_ONLY = "retrieval_only"


class RefusalReason(str, Enum):
    BELOW_THRESHOLD = "below_threshold"
    BUDGET_EXHAUSTED = "budget_exhausted"
    NAMESPACE_DENIED = "namespace_denied"
    CONTENT_POLICY = "content_policy"
    NO_RESULTS = "no_results"
