"""Evaluation-related enumerations and types."""
from __future__ import annotations

from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_score(cls, score: float, high_threshold: float = 0.85, low_threshold: float = 0.70) -> "ConfidenceLevel":
        if score >= high_threshold:
            return cls.HIGH
        if score >= low_threshold:
            return cls.MEDIUM
        return cls.LOW
