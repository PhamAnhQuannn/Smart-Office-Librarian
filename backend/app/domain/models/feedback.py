"""Domain model: Feedback."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Feedback:
    id: str
    query_log_id: str
    vote: str  # "up" | "down"
    user_id: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
