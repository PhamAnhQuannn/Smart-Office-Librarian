"""Domain model: ThresholdConfig (per-namespace similarity threshold)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ThresholdConfig:
    id: str
    namespace: str
    index_version: int
    threshold: float  # 0.0 .. 1.0, default 0.75
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
