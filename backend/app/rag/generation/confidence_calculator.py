"""Maps a primary cosine score to a human-readable confidence label.

Thresholds are taken from BASELINES.md Step 62 checkpoint values.
"""

from __future__ import annotations

# Confidence bands
_HIGH_THRESHOLD = 0.85
_MEDIUM_THRESHOLD = 0.70


def score_to_confidence(primary_cosine_score: float) -> str:
    """Return 'HIGH', 'MEDIUM', or 'LOW' based on primary cosine score."""
    if primary_cosine_score >= _HIGH_THRESHOLD:
        return "HIGH"
    if primary_cosine_score >= _MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"
