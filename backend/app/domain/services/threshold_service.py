"""Threshold service: retrieve and update similarity thresholds per namespace.

Fetches from the DB repository with fallback to the config default.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings


class ThresholdService:
    """Provides get/set threshold operations backed by the DB."""

    def __init__(self, thresholds_repo: Any | None = None) -> None:
        self._repo = thresholds_repo

    def get_threshold(self, *, namespace: str, index_version: int) -> float:
        """Return the configured threshold or the config default."""
        if self._repo is not None:
            record = self._repo.get_for_namespace(namespace, index_version)
            if record is not None:
                return float(record.threshold)
        return get_settings().default_threshold

    def update_threshold(
        self,
        *,
        namespace: str,
        index_version: int,
        threshold: float,
        updated_by: str | None = None,
    ) -> float:
        """Persist a new threshold value and return it."""
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        if self._repo is None:
            raise RuntimeError("ThresholdService requires a thresholds_repo")
        record = self._repo.upsert(
            namespace=namespace,
            index_version=index_version,
            threshold=threshold,
            updated_by=updated_by,
        )
        return float(record.threshold)
